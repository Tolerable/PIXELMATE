# PixelMate

![Screenshot-0001](https://github.com/user-attachments/assets/b572d4ca-19e3-458c-9997-df9160dc235a)

PixelMate is a dynamic AI-based conversational assistant that can generate image prompts and hold interactive conversations. It leverages Pollinations.ai for generating images and tracks time to provide a more natural conversational experience.

## Features:
- Engages in natural, flowing conversations.
- Generates images on the fly based on user prompts and inferences.
- Tracks the passage of time subtly to influence conversation flow (without explicitly mentioning it unless relevant).
- Capable of **vision analysis** based on images shared by users.

### Camera Button:
- **Left Click**: 
  - If text is in the input field, sends a **direct image request** based on the input and clears the field.
  - If no text is in the input field, it **repeats the last image prompt** used by either the user or the AI directly.
- **Right Click**: 
  - Inserts the **last image prompt** (either from the user or AI) back into the input field for editing.

### Magnifying Glass Button:
- **Left Click**: 
  - Opens a file dialog to select an image from the OS for **image-to-text conversion**. Displays the selected image and its generated description.
- **Right Click**: 
  - Pastes an image from the clipboard and processes it for **image-to-text conversion**. The description is sent **as if from the user**, with the message: `Image Shared With You: <description>`.

### Folder Button:
- **Left Click**: 
  - Opens the folder where all generated images are saved in the file explorer.

### Additional Notes:
- The **persona** is set directly in the script and is designed to create engaging and friendly interactions. The AI responds conversationally and generates image prompts based on user interaction.
- The AI uses **MRKDWN** to send prompts within the chat in character (this is not visible to the user).
- The persona is flexible, capable of adjusting to different narratives as driven by the user, including **NSFW content** generation (within reason).


## Getting Started:

1. Clone the repository:
   ```bash
   git clone https://github.com/Tolerable/PixelMate.git

Install the required libraries:

bash

pip install -r requirements.txt

Run the PixelMate app:

bash

    python pixelmate.py

Folder Structure:

    ./GENERATED/ - Folder where generated images will be stored.
    prompt_history.json - Stores the chat and prompt history.
    app_settings.json - Stores the user's app preferences.

To Do:

    Add more personalization options for users.
    Improve conversational context awareness based on time.
    Add more in-depth vision capabilities.

