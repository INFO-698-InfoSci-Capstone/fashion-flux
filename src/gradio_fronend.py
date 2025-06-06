import os
import gradio as gr
import requests
import json
from PIL import Image
import io
import base64
import sys

########################################
# Imports for video generation
# Add framepack to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'video_generation', 'framepack')))
from video_generation.framepack import framepack as fp

########################################


config = json.load(open("config.json"))

def person_example_fn(image_path):
    return image_path

def resize_image_to_buffer(image_path, size=(1024, 768), format="JPEG"):
    """
    Opens and resizes an image from a file path and returns an in-memory buffer.
    """
    img = Image.open(image_path).convert("RGB").resize(size)
    buffer = io.BytesIO()
    img.save(buffer, format=format)
    buffer.seek(0)
    return buffer


def submit_function(person_image, cloth_image, cloth_type, num_inference_steps, guidance_scale, seed):
    url = config["style_transfer_api"]

    # Resize images and get in-memory buffers
    person_buffer = resize_image_to_buffer(person_image)
    cloth_buffer = resize_image_to_buffer(cloth_image)

    files = {
        "person_image": ("person.jpg", person_buffer, "image/jpeg"),
        "cloth_image": ("cloth.jpg", cloth_buffer, "image/jpeg"),
    }

    data = {
        "config_json": json.dumps({
            "cloth_type": cloth_type,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "seed": seed
        })
    }
    
    response = requests.post(url, files=files, data=data)

    if response.status_code == 200:
        result = response.json()

        masked_image_bytes = base64.b64decode(result["masked_image"])
        result_image_bytes = base64.b64decode(result["result_image"])

        masked_img = Image.open(io.BytesIO(masked_image_bytes))
        result_img = Image.open(io.BytesIO(result_image_bytes))

        return masked_img, result_img
    else:
        raise RuntimeError(f"API error {response.status_code}: {response.text}")


# Function for pose transfer task
def pose_transfer_function(person_image, pose_image, num_inference_steps, guidance_scale, seed):
    url = config["pose_transfer_api"]

    with open(person_image, "rb") as f1, open(pose_image, "rb") as f2:
        files = {
            "person_image": ("person.jpg", f1, "image/jpeg"),
            "pose_image": ("pose.jpg", f2, "image/jpeg"),
        }
        data = {
            "config_json": json.dumps({
                #"cloth_type": cloth_type,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                "seed": seed
            })
        }

        response = requests.post(url, files=files, data=data)

    if response.status_code == 200:
        result = response.json()

        #masked_image_bytes = base64.b64decode(result["masked_image"])
        result_pose_bytes = base64.b64decode(result["result_pose"])

        #masked_img = Image.open(io.BytesIO(masked_image_bytes))
        result_pose = Image.open(io.BytesIO(result_pose_bytes))

        #return masked_img, result_img
        return result_pose
    else:
        raise RuntimeError(f"API error {response.status_code}: {response.text}")




HEADER = """
<h1 style="text-align: center;"> Fashion Flux: Your personal AI Stylist.</h1>
"""

def app_gradio():
    with gr.Blocks(title="Virtual-TryOn") as demo:
        gr.Markdown(HEADER)

        with gr.Tabs():

            # --- Style Transfer Tab ---
            with gr.Tab("Style Transfer"):
                with gr.Row():
                    root_path = "style_transfer/resource/demo/example"

                    with gr.Column(scale=1, min_width=300):
                        image_path = gr.Image(type="filepath", interactive=True, visible=False)
                        person_image = gr.Image(interactive=True, label="Person Image", type="filepath", height=400, width=300)
                        cloth_type = gr.Radio(
                            label="Try-On Cloth Type",
                            choices=["upper", "lower", "overall"],
                            value="upper",
                        )

                        with gr.Accordion("Advanced Options", open=False):
                            num_inference_steps = gr.Slider(
                                label="Inference Step", minimum=10, maximum=100, step=5, value=50
                            )
                            guidance_scale = gr.Slider(
                                label="CFG Strength", minimum=0.0, maximum=50, step=0.5, value=2.5
                            )
                            seed = gr.Slider(
                                label="Seed", minimum=-1, maximum=10000, step=1, value=42
                            )
                    with gr.Column(scale=1, min_width=300):
                        cloth_image = gr.Image(interactive=True, label="Condition Image", type="filepath", height=400, width=300)
                        submit_style = gr.Button("Submit Style Transfer")

                    with gr.Column(scale=3, min_width=600):
                        with gr.Row():
                            mask_image = gr.Image(interactive=False, label="Masked Image")
                            result_image = gr.Image(interactive=False, label="Result Image")

                        with gr.Row():
                            with gr.Column():
                                gr.Examples(
                                    examples=[os.path.join(root_path, "person", "men", f) for f in os.listdir(os.path.join(root_path, "person", "men"))],
                                    examples_per_page=4,
                                    inputs=image_path,
                                    label="Person Examples ①"
                                )
                            

                            with gr.Column():
                                gr.Examples(
                                    examples=[os.path.join(root_path, "condition", "upper", f) for f in os.listdir(os.path.join(root_path, "condition", "upper"))],
                                    examples_per_page=4,
                                    inputs=cloth_image,
                                    label="Condition Upper Examples"
                                )
                                gr.Examples(
                                    examples=[os.path.join(root_path, "condition", "overall", f) for f in os.listdir(os.path.join(root_path, "condition", "overall"))],
                                    examples_per_page=4,
                                    inputs=cloth_image,
                                    label="Condition Overall Examples"
                                )
                                gr.Examples(
                                    examples=[os.path.join(root_path, "condition", "person", f) for f in os.listdir(os.path.join(root_path, "condition", "person"))],
                                    examples_per_page=4,
                                    inputs=cloth_image,
                                    label="Condition Reference Person Examples"
                                )

                image_path.change(person_example_fn, inputs=image_path, outputs=person_image)
                submit_style.click(
                    fn=submit_function,
                    inputs=[
                        person_image,
                        cloth_image,
                        cloth_type,
                        num_inference_steps,
                        guidance_scale,
                        seed
                    ],
                    outputs=[mask_image, result_image],
                )


            # --- Pose Transfer Tab ---
            with gr.Tab("Pose Transfer"):
                with gr.Row():
                    pose_root_path = "pose_transfer/test_input_images"

                    with gr.Column(scale=1, min_width=400):
                        pose_image_path = gr.Image(type="filepath", interactive=True, visible=False)
                        person_img = gr.Image(interactive=True, label="Person Image", type="filepath", height=600)

                        with gr.Accordion("Advanced Options", open=False):
                            steps_pose = gr.Slider(
                                label="Step pose", minimum=10, maximum=100, step=5, value=80
                            )
                            scale_pose = gr.Slider(
                                label="CFG Strength", minimum=0.0, maximum=50, step=0.5, value=2.2
                            )
                            seed_pose = gr.Slider(
                                label="Seed", minimum=-1, maximum=10000, step=1, value=42
                            )
                    with gr.Column(scale=1, min_width=400):
                        pose_img = gr.Image(interactive=True, label="Pose Image", type="filepath", height=600)
                        submit_pose = gr.Button("Submit Pose Transfer")

                    with gr.Column(scale=3, min_width=300):
                        with gr.Row():
                            result_pose = gr.Image(interactive=False, label="Result Image")
                        with gr.Row():
                            with gr.Column():
                                gr.Examples(
                                    examples=[os.path.join(pose_root_path, "Person", f) for f in os.listdir(os.path.join(pose_root_path, "Person"))],
                                    examples_per_page=5,
                                    inputs=person_img,
                                    label="Person Examples"
                                )

                            with gr.Column():
                                gr.Examples(
                                    examples=[os.path.join(pose_root_path, "Pose", f) for f in os.listdir(os.path.join(pose_root_path, "Pose"))],
                                    examples_per_page=5,
                                    inputs=pose_img,
                                    label="Pose Examples"
                                )
                submit_pose.click(
                     fn=pose_transfer_function,
                     inputs=[person_img, pose_img, steps_pose, scale_pose, seed_pose],
                     outputs=result_pose,
                 )

            
            # --- Reel Generation Tab ---
            with gr.Tab("Reel Generation"):
                #fp.initialize_framepack()
                quick_prompts = [
                    'The model poses gracefully  for a photoshoot, she smiles and shows her dress. The camera takes a full body shot and then zooms in on her face.',
                    'A character doing some simple body movements. posing for a photoshoot and short video movie shooting.',
                ]
                quick_prompts = [[x] for x in quick_prompts]

                with gr.Row():
                    with gr.Column():
                        input_image = gr.Image(sources='upload', type="numpy", label="Image", height=320)
                        prompt = gr.Textbox(label="Prompt", value='')
                        example_quick_prompts = gr.Dataset(samples=quick_prompts, label='Quick List', samples_per_page=1000, components=[prompt])
                        example_quick_prompts.click(lambda x: x[0], inputs=[example_quick_prompts], outputs=prompt, show_progress=False, queue=False) 

                        # Generation Buttons
                        with gr.Row():
                            start_button = gr.Button(value="Start Generation")
                            end_button = gr.Button(value="End Generation", interactive=False)
                        
                        with gr.Group():
                            use_teacache = gr.Checkbox(label='Use TeaCache', value=True, info='Faster speed, but often makes hands and fingers slightly worse.')

                            n_prompt = gr.Textbox(label="Negative Prompt", value="", visible=False)  # Not used
                            seed = gr.Number(label="Seed", value=31337, precision=0)

                            total_second_length = gr.Slider(label="Total Video Length (Seconds)", minimum=1, maximum=120, value=5, step=0.1)
                            latent_window_size = gr.Slider(label="Latent Window Size", minimum=1, maximum=33, value=9, step=1, visible=False)  # Should not change
                            steps = gr.Slider(label="Steps", minimum=1, maximum=100, value=25, step=1, info='Changing this value is not recommended.')

                            cfg = gr.Slider(label="CFG Scale", minimum=1.0, maximum=32.0, value=1.0, step=0.01, visible=False)  # Should not change
                            gs = gr.Slider(label="Distilled CFG Scale", minimum=1.0, maximum=32.0, value=10.0, step=0.01, info='Changing this value is not recommended.')
                            rs = gr.Slider(label="CFG Re-Scale", minimum=0.0, maximum=1.0, value=0.0, step=0.01, visible=False)  # Should not change

                            gpu_memory_preservation = gr.Slider(label="GPU Inference Preserved Memory (GB) (larger means slower)", minimum=6, maximum=128, value=6, step=0.1, info="Set this number to a larger value if you encounter OOM. Larger value causes slower speed.")

                            mp4_crf = gr.Slider(label="MP4 Compression", minimum=0, maximum=100, value=16, step=1, info="Lower means better quality. 0 is uncompressed. Change to 16 if you get black outputs. ")


                    with gr.Column():
                        preview_image = gr.Image(label="Next Latents", height=200, visible=False)
                        result_video = gr.Video(label="Finished Frames", autoplay=True, show_share_button=False, height=512, loop=True)
                        gr.Markdown('Note that the ending actions will be generated before the starting actions due to the inverted sampling. If the starting action is not in the video, you just need to wait, and it will be generated later.')
                        progress_desc = gr.Markdown('', elem_classes='no-generating-animation')
                        progress_bar = gr.HTML('', elem_classes='no-generating-animation')


                ips = [input_image, prompt, n_prompt, seed, total_second_length, latent_window_size, steps, cfg, gs, rs, gpu_memory_preservation, use_teacache, mp4_crf]
                start_button.click(fn=fp.process_with_nsfw_check, 
                                   inputs=ips, 
                                   outputs=[result_video, preview_image, progress_desc, progress_bar, start_button, end_button]
                                )
                end_button.click(fn=fp.end_process)
                

    demo.queue().launch(share=True, show_error=True)

if __name__ == "__main__":
    app_gradio()
