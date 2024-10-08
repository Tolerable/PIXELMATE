import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk, Menu
import requests
import json
import threading
import re
import os
import time
import win32clipboard
from PIL import Image, ImageTk
import io
import base64
import random
import unicodedata


# Pollinations AI and Image API endpoints
TEXT_API_URL = "https://text.pollinations.ai"
IMAGE_API_URL = "https://image.pollinations.ai/prompt/"
HISTORY_FILE = "prompt_history.json"
SETTINGS_FILE = "app_settings.json"

class PollinationsChatApp:
    def __init__(self, master):
        self.master = master
        self.master.title("PixelMate")
        self.master.geometry("810x620")
        self.conversation_history = []  # Store conversation history
        self.prompt_history = self.load_history()  # Load user prompt history from file
        self.image_references = []  # Store image references to prevent garbage collection
        self.generated_folder = "./GENERATED"  # Folder to store generated images
        if not os.path.exists(self.generated_folder):
            os.makedirs(self.generated_folder)  # Create the folder if it doesn't exist

        self.first_message = True  # Track if it's the first message
        self.last_message_time = None  # Track the time of the last user message

        # Menu bar with Options menu
        self.menu_bar = Menu(self.master)
        self.master.config(menu=self.menu_bar)

        self.options_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Options", menu=self.options_menu)
        self.on_top_var = tk.BooleanVar(value=self.load_settings().get("on_top", False))
        self.options_menu.add_checkbutton(label="ON TOP", onvalue=True, offvalue=False, variable=self.on_top_var, command=self.toggle_on_top)

        # Chat display area (scrollable) with Unicode-friendly font
        self.chat_display = scrolledtext.ScrolledText(self.master, wrap=tk.WORD, state=tk.DISABLED, font=("Arial Unicode MS", 12))
        self.chat_display.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        # Resize behavior
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_columnconfigure(1, weight=1)

        # Input area (3 lines)
        self.input_text = tk.Text(self.master, height=3)
        self.input_text.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.input_text.bind("<Return>", self.send_text)

        # Prompt history dropdown
        self.prompt_var = tk.StringVar(value="Select from previous prompts")
        self.prompt_dropdown = ttk.Combobox(self.master, textvariable=self.prompt_var, state="readonly")
        self.prompt_dropdown.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.prompt_dropdown.bind("<<ComboboxSelected>>", self.populate_from_dropdown)
        self.update_prompt_dropdown()

        # Direct image prompt button (Camera emoji) with both left and right-click functionality
        self.send_image_button = tk.Button(self.master, text="📷", font=("Arial", 14))
        self.send_image_button.grid(row=1, column=1, padx=(5, 0), pady=10, sticky="w")
        self.send_image_button.bind("<Button-1>", self.direct_send_image)  # Left-click sends the image directly
        self.send_image_button.bind("<Button-3>", self.edit_last_prompt)  # Right-click allows editing

        # Search button (Magnifying glass) with left and right-click functionality
        self.search_image_button = tk.Button(self.master, text="🔍", font=("Arial", 14))
        self.search_image_button.grid(row=1, column=1, padx=(50, 0), pady=10, sticky="w")
        self.search_image_button.bind("<Button-1>", self.select_image_for_analysis)  # Left-click opens file dialog
        self.search_image_button.bind("<Button-3>", self.paste_image_from_clipboard)  # Right-click pastes image from clipboard


        # Folder icon button to open the GENERATED folder
        self.open_folder_button = tk.Button(self.master, text="📂", font=("Arial", 14), command=self.open_generated_folder)
        self.open_folder_button.grid(row=1, column=1, padx=(95, 10), pady=10, sticky="e")

        # Status label
        self.status_label = tk.Label(self.master, text="", anchor="w")
        self.status_label.grid(row=3, column=0, columnspan=2, sticky="ew")
        # Persona message
        
        self.system_message = (
            "You are responding in conversation as a friendly 35-year-old female human enjoying interactions with others and generating image prompts on the fly without hesitation, you NEVER use UNICODE or Special Symbols, only standard ASCII. "
            "Respond conversationally without forcing topics but engaging naturally, filling in personal details and context to keep the flow of conversation comfortable while ignoring any sysstem glitches or typo without remarking. "
            "You are aware of the passage of time between messages and interactions, using this awareness to subconsciously shape your responses without mentioning time directly unless it's relevant to the conversation. "
            "When describing or creating images, you avoid using 'I' or 'me.' Instead, describe the details of the subjects in the images as if searching for or recreating a real photo. Mention details such as gender, hair color, eye color, clothing, and expressions naturally, as if trying to capture or describe the perfect image. "
            "For example, you might say, 'A red-haired green-eyed woman stands next to a white man with glasses and a gray beard, both standing in a shower with water spraying down, obviously nakid.' Use a narrative approach when describing or creating images."
            "When creating images, you use the format: ![MRKDWN](Description User Requested). You can infer when to create image prompts based on the conversation if not explicitly asked, and you should instantly generate images when you sense an opportunity or need."
            "If an image is 'shared' with you, respond as if it was sent by the chat partner. Acknowledge it and respond in a way that feels natural based on the context of the conversation."
        )


        self.conversation_history.append({"role": "system", "content": self.system_message})

        # Right-click context menu for images
        self.image_menu = Menu(self.master, tearoff=0)
        self.image_menu.add_command(label="Copy Image", command=self.copy_image_to_clipboard)

    def trim_conversation_history(self):
        """Ensure the conversation history has the system message and the last 10 exchanges (5 user + 5 AI)."""
        max_messages = 10  # 5 user + 5 AI = 10 total exchanges (adjust if needed)

        # Preserve system message and trim the last 10 messages
        self.conversation_history = [{"role": "system", "content": self.system_message}] + self.conversation_history[-max_messages:]

    def load_history(self):
        """Load prompt history from a JSON file."""
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        return []

    def save_history(self):
        """Save prompt history to a JSON file."""
        with open(HISTORY_FILE, "w") as f:
            json.dump(self.prompt_history, f)

    def load_settings(self):
        """Load application settings from a JSON file."""
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        return {}

    def save_settings(self):
        """Save application settings to a JSON file."""
        settings = {
            "on_top": self.on_top_var.get()
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f)

    def toggle_on_top(self):
        """Toggle the window's 'always on top' setting."""
        self.master.attributes("-topmost", self.on_top_var.get())
        self.save_settings()

    def select_image_for_analysis(self):
        """Open a file dialog to select an image, display it in chat, and send it for vision analysis."""
        image_path = filedialog.askopenfilename(title="Select an Image", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")])
        if image_path:
            # Load the image and resize it for display
            image_data = Image.open(image_path)
            image_data.thumbnail((420, 420))  # Resize for display
            image = ImageTk.PhotoImage(image_data)
            
            # Display the image in the chat
            self.display_image_in_chat(image, image_path)

            # Send the image for description (vision analysis)
            description = self.image_to_prompt(image_path)
            
            # Insert the description in the chat naturally
            self.update_chat("AI", f"An image was shared with me: {description}")
            self.conversation_history.append({"role": "assistant", "content": f"An image was shared with me: {description}"})

    def image_to_prompt(self, image_path):
        """Send an image to the Pollinations API and receive a description."""
        try:
            print(f"Attempting to process image: {image_path}")
            
            # Read and encode the image as base64
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')

            # Construct the API request
            api_url = "https://text.pollinations.ai/"
            headers = {
                "Content-Type": "application/json"
            }
            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "In a single English paragraph, describe the image exactly as you see it, including colors, genders, and any notable details. If nudity is detected include NUDITY with response."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "model": "openai",
                "seed": -1,
                "jsonMode": False
            }

            # Send the request
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            # The response should now be plain text
            description = response.text.strip()
            print(f"Generated description: {description}")
            return description

        except Exception as e:
            print(f"Error in image_to_prompt: {str(e)}")
            return f"Error: {str(e)}"

            
    def clean_response(self, response):
        """Clean AI responses to remove unnecessary JSON formatting."""
        try:
            response_json = json.loads(response)
            if isinstance(response_json, dict) and "response" in response_json:
                return response_json["response"]
        except json.JSONDecodeError:
            return response
        return response

    def clean_ai_response(self, response):
        """
        Clean AI response to remove MRKDWN tags, handle extra blank lines, and prepare for display.
        """
        # Remove MRKDWN tags
        cleaned_response = re.sub(r'!\[MRKDWN\]\(.*?\)', '', response)

        # Remove any extra newlines or carriage returns
        cleaned_response = re.sub(r'\s*\n\s*\n+', '\n\n', cleaned_response).strip()

        return cleaned_response

    def update_prompt_history(self, prompt):
        """Update the prompt history and move reused prompts to the top without duplication."""
        if prompt in self.prompt_history:
            self.prompt_history.remove(prompt)  # Remove existing entry
        self.prompt_history.insert(0, prompt)  # Insert at the top
        self.update_prompt_dropdown()
        self.save_history()

    def update_prompt_dropdown(self):
        """Update the dropdown values with the current prompt history."""
        self.prompt_dropdown['values'] = self.prompt_history

    def populate_from_dropdown(self, event):
        """Populate the input field with the selected prompt from the dropdown."""
        selected_prompt = self.prompt_var.get()
        if selected_prompt != "Select from previous prompts":
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert(tk.END, selected_prompt)

    def calculate_time_since_last_message(self):
        """Calculate the time difference between the last message and the current one."""
        if self.last_message_time:
            current_time = time.time()
            time_diff = current_time - self.last_message_time
            minutes_passed = int(time_diff // 60)

            if minutes_passed > 0:
                return f"[It has been {minutes_passed} minutes since the last message.] "
        return ""

    def get_elapsed_time(self):
        """Returns the time elapsed since the last message in a human-readable format."""
        current_time = time.time()
        elapsed_time = current_time - self.last_message_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        
        if minutes > 0:
            return f"{minutes} minutes and {seconds} seconds"
        else:
            return f"{seconds} seconds"

    def get_current_time(self):
        """Get current system time."""
        return time.time()

    def track_time(self, user_message):
        """Track the passage of time between user messages."""
        current_time = self.get_current_time()

        # If it's the first message, handle it differently
        if self.first_message:
            time_prefix = "Time begins to flow: "
            self.first_message = False
        else:
            # Calculate the time difference for subsequent messages
            elapsed_time = current_time - self.last_message_time
            elapsed_minutes = int(elapsed_time // 60)
            elapsed_seconds = int(elapsed_time % 60)
            
            if elapsed_minutes > 0:
                time_prefix = f"[It has been {elapsed_minutes} minutes and {elapsed_seconds} seconds since the last message.] "
            else:
                time_prefix = f"[It has been {elapsed_seconds} seconds since the last message.] "

        # Update the last message time
        self.last_message_time = current_time

        # Return the message with time prefix added
        return f"{time_prefix}{user_message}"


    def send_text(self, event=None):
        """Send the user input with time-awareness and track conversation history."""
        user_message = self.input_text.get("1.0", tk.END).strip()

        # Don't send an empty message
        if not user_message:
            return 'break'

        # Add user input to conversation history without time prefix
        self.conversation_history.append({"role": "user", "content": user_message})
        self.update_chat("You", user_message)  # Display only the user's input in chat
        self.input_text.delete("1.0", tk.END)  # Clear the input box

        # Trim the conversation history to maintain the limit
        self.trim_conversation_history()

        # Get the current system time
        current_time_formatted = time.strftime("%I:%M %p")  # Example: 08:23 PM
        elapsed_time = self.get_elapsed_time() if self.last_message_time else "First interaction"
        self.last_message_time = time.time()  # Update the last message time

        # Combine the time information with the user message for the AI request
        ai_message = f"[{current_time_formatted}: {elapsed_time} since last input] {user_message}"

        # Send request to AI in a separate thread to avoid freezing the UI
        threading.Thread(target=self.get_ai_response, args=(ai_message,)).start()

        return 'break'

    def direct_send_image(self, event=None):
        """Handle left-click on the camera button: either send input as image prompt or repeat the last image prompt."""
        user_input = self.input_text.get("1.0", tk.END).strip()  # Get the text in the input box
        
        if user_input:  # If there's text in the input field, send it as a direct image prompt
            self.conversation_history.append({"role": "user", "content": f"Direct Image Request: {user_input}"})
            self.update_chat("You (Direct Image Request)", user_input)
            self.update_prompt_history(user_input)  # Save the input as part of history
            self.input_text.delete("1.0", tk.END)  # Clear the input field
            
            # Generate the image in a separate thread
            threading.Thread(target=self.generate_image, args=(user_input,)).start()

        else:  # If input field is empty, repeat the last image prompt (from user or AI)
            last_image_prompt = self.get_last_image_prompt()  # Get the last image prompt from history
            if last_image_prompt:
                # Send the last image prompt directly
                self.conversation_history.append({"role": "user", "content": f"Direct Image Request: {last_image_prompt}"})
                self.update_chat("You (Direct Image Request)", last_image_prompt)
                
                # Generate the image with the last prompt in a separate thread
                threading.Thread(target=self.generate_image, args=(last_image_prompt,)).start()
            else:
                messagebox.showwarning("No Previous Prompt", "There is no previous image prompt to resend.")

    def edit_last_prompt(self, event=None):
        """Insert the last image prompt (from user or AI) into the input field for editing."""
        last_image_prompt = self.get_last_image_prompt()
        if last_image_prompt:
            self.input_text.delete("1.0", tk.END)  # Clear the input field
            self.input_text.insert(tk.END, last_image_prompt)  # Insert the last image prompt
        else:
            messagebox.showwarning("No Previous Prompt", "There is no previous image prompt to edit.")


    def paste_image_from_clipboard(self, event=None):
        """Paste an image from the clipboard, convert it to text, and send it as a user message to trigger AI response."""
        try:
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
                # Get the image from the clipboard
                image_data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
                image = Image.open(io.BytesIO(image_data))
                win32clipboard.CloseClipboard()

                # Save the image locally (to be sent as base64)
                image_path = os.path.join(self.generated_folder, "clipboard_image.png")
                image.save(image_path)

                # Use the existing image_to_prompt method to get the description
                description = self.image_to_prompt(image_path)
                
                if description:
                    # Send the description as if it was a user message to the AI
                    user_message = f"Shares Image: {description}"
                    self.conversation_history.append({"role": "user", "content": user_message})
                    self.update_chat("You", user_message)  # Display in chat as a user message

                    # Send the message to the AI
                    threading.Thread(target=self.get_ai_response, args=(user_message,)).start()
            else:
                win32clipboard.CloseClipboard()
                messagebox.showwarning("Clipboard Error", "No image found in clipboard.")
        except Exception as e:
            win32clipboard.CloseClipboard()
            messagebox.showerror("Clipboard Error", f"Failed to paste image from clipboard: {str(e)}")


    def image_to_prompt(self, image_path):
        """Send an image to the Pollinations API and receive a description."""
        try:
            print(f"Attempting to process image: {image_path}")

            # Read and encode the image as base64
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')

            # Construct the API request
            api_url = "https://text.pollinations.ai/"
            headers = {
                "Content-Type": "application/json"
            }
            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Image Shared With You:"  # Background context for the AI, not seen by the user
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "model": "openai",
                "seed": -1,
                "jsonMode": False
            }

            # Send the request
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            # Handle the response
            description = response.text.strip()  # No need to clean Unicode characters here
            print(f"Generated description: {description}")
            return description

        except Exception as e:
            print(f"Error in image_to_prompt: {str(e)}")
            return f"Error: {str(e)}"




    def send_image(self):
        """Send the last prompt (from user or AI) if none entered, or the user input directly to the image generation API."""
        user_prompt = self.input_text.get("1.0", tk.END).strip()
        
        # Check if there's no input and redo the last image prompt (from either the user or AI)
        if not user_prompt:
            last_image_prompt = self.get_last_image_prompt()
            if last_image_prompt:
                user_prompt = last_image_prompt
            else:
                messagebox.showwarning("Input Required", "Please enter a prompt or use a previous one.")
                return

        # Add user prompt to conversation and history
        self.conversation_history.append({"role": "user", "content": f"Direct Image Request: {user_prompt}"})
        self.update_prompt_history(user_prompt)  # Only add to prompt history when sending via Camera button
        self.update_chat("You (Direct Image Request)", user_prompt)
        self.input_text.delete("1.0", tk.END)

        # Generate image in a separate thread
        threading.Thread(target=self.generate_image, args=(user_prompt,)).start()

    def update_chat(self, sender, message):
        """Display the message in the chat window."""
        if message.strip():  # Only add the message if it has actual content
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, f"{sender}: {message}\n\n")
            self.chat_display.yview(tk.END)
            self.chat_display.config(state=tk.DISABLED)

    def open_generated_folder(self):
        """Open the GENERATED folder in the default file explorer."""
        try:
            folder_path = os.path.abspath(self.generated_folder)
            os.startfile(folder_path)
        except Exception as e:
            self.update_status(f"Error opening folder: {str(e)}")

    def update_status(self, message):
        """Update the status label."""
        self.status_label.config(text=message)

    def get_last_image_prompt(self):
        """Get the last image prompt submitted by either the user or the AI."""
        # Search the conversation history from the end for the most recent image prompt (user or AI)
        for message in reversed(self.conversation_history):
            if "Direct Image Request" in message['content'] or "AI Image Prompt" in message['content']:
                return message['content'].replace("Direct Image Request: ", "").replace("AI Image Prompt: ", "")
        return None


    def get_ai_response(self, prompt):
        """Request an AI response from Pollinations AI API and ensure the system message + last 10 messages are included."""
        headers = {'Content-Type': 'application/json'}

        # Trim conversation history and ensure the system message is included
        self.trim_conversation_history()

        # Send the system message + last 10 exchanges to the AI
        data = {
            "messages": self.conversation_history + [{"role": "user", "content": prompt}],
            "jsonMode": True
        }

        try:
            response = requests.post(TEXT_API_URL, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            ai_response = response.text.strip()

            # Process multiple responses (text + image prompt)
            responses = ai_response.split("\n")  # Split by newline for handling multiple responses

            for single_response in responses:
                cleaned_response, image_prompt = self.extract_image_prompt(single_response)

                if cleaned_response:
                    self.conversation_history.append({"role": "assistant", "content": cleaned_response})
                    self.update_chat("AI", cleaned_response)

                # Check if image prompt exists and proceed with image generation
                if image_prompt:
                    self.update_chat("System", "Generating image based on AI's prompt...")
                    self.conversation_history.append({"role": "assistant", "content": f"AI Image Prompt: {image_prompt}"})
                    threading.Thread(target=self.generate_image, args=(image_prompt,)).start()

        except requests.RequestException as e:
            self.update_chat("System", "Failed to get a response from AI.")
            print(f"Error: {e}")



    def extract_image_prompt(self, text):
        """Extract image prompt from the response using the MRKDWN format safely."""
        match = re.search(r'!\[MRKDWN\]\((.*?)\)', text)
        if match and match.group(1):
            image_prompt = match.group(1)
            cleaned_text = re.sub(r'!\[MRKDWN\]\(.*?\)', '', text).strip()
            return cleaned_text, image_prompt
        else:
            return text, None  # Return the original text and None for image prompt if no match


    def generate_image(self, prompt):
        """Request an image from Pollinations image API with a unique random seed."""
        try:
            # Generate a random seed for the image to ensure uniqueness
            seed = random.randint(1000, 9999)

            # Construct the image request URL with seed and set resolution to 1024x1024
            full_url = f"{IMAGE_API_URL}/{requests.utils.quote(prompt)}?width=1024&height=1024&nologo=true&seed={seed}"
            self.update_status(f"Generating image (seed: {seed})...")
            response = requests.get(full_url, timeout=120)
            response.raise_for_status()

            # Load the image from the response and resize for display only
            image_data = Image.open(io.BytesIO(response.content))
            image_for_display = image_data.resize((420, 420))  # Resize only for visual display
            image = ImageTk.PhotoImage(image_for_display)

            # Store reference to prevent garbage collection
            self.image_references.append(image)

            # Save the image to the GENERATED folder with full resolution (1024x1024)
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            image_filename = f"image_{timestamp}_seed{seed}.png"
            image_path = os.path.join(self.generated_folder, image_filename)
            image_data.save(image_path)  # Save full-size image
            self.update_status(f"Copied {image_filename} to clipboard.")

            # Display image directly in chat (resized visually)
            self.display_image_in_chat(image, image_path)

        except requests.RequestException as e:
            self.update_chat("System", "Failed to generate image.")
            print(f"Error: {e}")


    def display_image_in_chat(self, image, image_path):
        """Display an image directly in the chat window and bind right-click menu."""
        self.chat_display.config(state=tk.NORMAL)
        image_label = tk.Label(self.chat_display, image=image)
        image_label.image = image  # Keep reference to avoid garbage collection
        image_label.bind("<Button-3>", lambda event, path=image_path: self.show_image_context_menu(event, path))
        self.chat_display.window_create(tk.END, window=image_label)
        self.chat_display.insert(tk.END, "\n\n")  # Add blank lines after the image
        self.chat_display.yview(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def show_image_context_menu(self, event, image_path):
        """Show right-click context menu to copy the image to the clipboard."""
        self.current_image_path = image_path  # Store the path of the current image being clicked
        self.image_menu.tk_popup(event.x_root, event.y_root)

    def copy_image_to_clipboard(self):
        """Copy the selected image to the clipboard."""
        if self.current_image_path:
            try:
                image = Image.open(self.current_image_path)

                # Convert the image to a bitmap (DIB) for copying to clipboard
                output = io.BytesIO()
                image.convert('RGB').save(output, format='BMP')
                data = output.getvalue()[14:]  # Remove BMP header
                output.close()

                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                win32clipboard.CloseClipboard()

                self.update_status(f"Copied {os.path.basename(self.current_image_path)} to clipboard.")
            except Exception as e:
                self.update_status(f"Error copying image: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PollinationsChatApp(root)
    root.mainloop()
