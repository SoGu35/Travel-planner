import gradio as gr
from maps import *
from chatbot import *

# Gradio Interface
with gr.Blocks() as demo: 
    # Hidden States
    generated_locations = gr.State("")
    selected_coords_state = gr.State([])
    encoded_polyline_state = gr.State("")
    routedata_state = gr.State({})
    selected_locations_state = gr.State([]) 
    state = gr.State([])  # chat history state
    # Interactive components
    with gr.Row(scale = 2):
        with gr.Column(scale = 1):
            chatbot = gr.Chatbot(label="Llama3.2 Ze Planner", height=500, type = "messages")
            msg = gr.Textbox(placeholder="e.g. Plan me a 3 day trip to Korea", elem_id= "input-box",  show_label=False)
            generate_route_button = gr.Button("Generate Route")
            clear_btn = gr.Button("Clear Chat")
        with gr.Column(scale = 1):
            map_display = gr.HTML()
            route_display = gr.Textbox(label = "Suggested Route", interactive=False, visible=True)
    with gr.Row(scale = 1):
        input_box = gr.Textbox(label="Add Location", interactive=True)
        suggestion_buttons = [gr.Button(visible=False, scale=1) for _ in range(5)]
        output_box = gr.Textbox(label="Selected Locations", interactive=False)

########################################################################################################################
    # Logic when buttons are clicked
    # Chatbot Submission
    msg.submit(llama_stream, inputs=[msg, state], outputs=[chatbot, state, generated_locations]).then(
        fn = extract_loc_from_reply, inputs=[generated_locations], outputs = [generated_locations]
    ).then(
        add_generated_locations_to_map, # Add generated locations to map
        inputs=[generated_locations, selected_locations_state], outputs=[routedata_state, encoded_polyline_state, map_display, output_box]
    ).then(
        fn=extract_route_info,
        inputs=[routedata_state],
        outputs=[route_display]
    )
    msg.submit(lambda: "", None, msg)  # Clear input box after sending message
    # Clear chatbot state
    clear_btn.click(fn=clear_all, outputs=[selected_locations_state, chatbot,state,generated_locations,selected_coords_state,encoded_polyline_state,routedata_state,map_display,route_display,output_box,msg,input_box])  # Resets   
    # Manual Search box + suggestions
    input_box.change(show_suggestions, inputs=input_box, outputs=suggestion_buttons)
    for btn in suggestion_buttons:
        btn.click(
            fn=add_locations,
            inputs=[btn, selected_locations_state],
            outputs=[output_box, selected_coords_state]
        )
    # Manual route generation
    generate_route_button.click(
        fn=plot_map,
        inputs=[selected_coords_state],
        outputs=[routedata_state, encoded_polyline_state, map_display]
    ).then(
        fn = extract_route_info,
        inputs=[routedata_state],
        outputs=[route_display]
    )
    # Initial prompt to chatbot
    demo.load(fn=init_prompt, outputs=[chatbot, state])  # Load initial prompt and
demo.launch()
