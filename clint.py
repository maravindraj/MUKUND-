import requests
import base64
import pygame
import pyttsx3

data_to_be_sent = {
    'latt': '8.3',
    'longi':'79.21'
}

url = 'http://127.0.0.1:5001/route11'

response = requests.post(url, data = data_to_be_sent)

def play_warning_sound_for_duration(duration=10):
    """
    Plays a warning siren sound for the specified duration (in seconds).
    """
    try:
        pygame.mixer.music.load(SIREN_SOUND_PATH)  # Load the siren sound file
        pygame.mixer.music.play(-1)  # Play the sound on loop
        pygame.time.wait(duration * 1000)  # Wait for the specified duration in milliseconds
    finally:
        pygame.mixer.music.stop()  # Stop the sound after the duration

# Function to speak the warning using text-to-speech
def voice_warning(message):
    """
    This function uses the pyttsx3 library to generate voice warnings.
    """
    engine.say(message)
    engine.runAndWait()

if response.status_code == 200:
    data = response.json()
    print(data)
    print('distance : ', data['distance_to_nearest'])
    distance_to_nearest = data['distance_to_nearest']   

    # Initialize pygame mixer for sound
    pygame.mixer.init()
    
    # Initialize text-to-speech engine
    engine = pyttsx3.init()
    
    # Define the path to the police siren sound file
    SIREN_SOUND_PATH = r"C:\Users\Aravind\Downloads\capestone 1\mixkit-police-siren-us-1643.wav" 
    safe_water=data['safe_water']
    if not safe_water:  # If the user is in danger
        warning_message = (
            f"Warning! You are {distance_to_nearest:.2f} kilometers away from the border. "
            f"You are in a danger zone. Change your course immediately!"
        )
        play_warning_sound_for_duration(duration=10)  # Play warning sound
        voice_warning(warning_message)  # Speak warning
    else:  # If the user is safe
        safe_message = (
            f"Safe: You are {distance_to_nearest:.2f} kilometers away from the border. "
            f"Continue your journey carefully."
        )
        voice_warning(safe_message)

    filess = base64.b64decode(data['file_content'])
    with open('MUKUND111.html', 'wb') as main_file:
        main_file.write(filess)
    print('DOne')
else:
    print(f'Exited with error code : {response.status_code}') 
    