#!/usr/bin/env python2

import os
import math
import random
import pygame
import st7789
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from time import sleep, time
import logging
from datetime import datetime
import traceback

log_filename = f"valplayer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Button GPIO pins
BUTTON_A = 5
BUTTON_B = 6
BUTTON_X = 16
BUTTON_Y = 24

# Display setup for Pirate Audio
disp = st7789.ST7789(
    height=240,
    width=240,
    rotation=90,
    port=0,
    cs=1,
    dc=9,
    backlight=13,
    spi_speed_hz=80 * 1000 * 1000,
    offset_left=0,
    offset_top=0
)

# Initialize display
disp.begin()

# Crystal Red color scheme
COLORS = {
    'background': (40, 0, 0),      # Deep crystal red
    'text': (255, 220, 220),       # Soft crystal white
    'accent': (255, 0, 0),         # Pure red
    'glow': (255, 40, 40),         # Red glow
    'shadow': (20, 0, 0),          # Deep shadow
    'crystal': (255, 180, 180)     # Crystal highlight
}

# Font configuration
FONT_SIZES = {
    'title': 22,
    'info': 18,
    'status': 16,
    'sleep_title': 32
}

# Music player configuration
MUSIC_DIR = "/media/usb/Music"
FALLBACK_MUSIC_DIR = os.path.expanduser("~/Music")
songs = []
current_track = 0
playing = False
error_count = 0
volume = 0.5

# Sleep mode configuration
SLEEP_TIMEOUT = 300  # 5 minutes in seconds
last_activity_time = time()
is_sleeping = False

# Visualization configuration
viz_bars = 12
viz_heights = [0] * viz_bars
viz_targets = [0] * viz_bars
viz_speed = 0.3

# Text scrolling configuration
scroll_position = 0
scroll_speed = 2
scroll_pause = 30
scroll_pause_counter = 0
SCROLL_WIDTH = 200

def load_songs():
    """Load all music files from the USB MUSIC_DIR with fallback"""
    global songs
    songs = []

    def try_load_from_dir(directory):
        """Helper function to attempt loading from a specific directory"""
        found_songs = []
        try:
            # Check if directory exists and is accessible
            if os.path.exists(directory) and os.path.isdir(directory):
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        if file.lower().endswith(('.mp3', '.wav', '.ogg')):
                            found_songs.append(os.path.join(root, file))
                found_songs.sort()
                logging.info(f"Successfully loaded {len(found_songs)} songs from {directory}")
                return found_songs
            else:
                logging.warning(f"Music directory {directory} is not accessible")
                return []
        except Exception as e:
            logging.error(f"Error loading songs from {directory}: {str(e)}")
            return []

    # First try to load from USB
    songs = try_load_from_dir(MUSIC_DIR)

    # If no songs found on USB, try fallback directory
    if not songs:
        logging.warning(f"No songs found in {MUSIC_DIR}, trying fallback directory")
        songs = try_load_from_dir(FALLBACK_MUSIC_DIR)
        if songs:
            logging.info("Successfully loaded songs from fallback directory")
        else:
            logging.warning("No songs found in fallback directory either")

    # Create directories if they don't exist
    os.makedirs(MUSIC_DIR, exist_ok=True)
    os.makedirs(FALLBACK_MUSIC_DIR, exist_ok=True)

    # Print status
    if songs:
        print(f"Loaded {len(songs)} songs from {'USB' if songs[0].startswith(MUSIC_DIR) else 'fallback directory'}")
    else:
        print("No music files found in either USB or fallback directory")

def create_sleep_screen():
    """Create the sleep screen with logo and text"""
    try:
        # Load and resize background image
        sleep_image = Image.open("valpy.png")
        sleep_image = sleep_image.resize((240, 240), Image.Resampling.LANCZOS)

        # Create drawing object
        draw = ImageDraw.Draw(sleep_image)

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
                                    FONT_SIZES['sleep_title'])
        except:
            font = ImageFont.load_default()

        # Add "THE" text
        the_text = "THE"
        the_bbox = draw.textbbox((0, 0), the_text, font=font)
        the_width = the_bbox[2] - the_bbox[0]
        the_x = (240 - the_width) // 2

        # Add shadow for "THE"
        draw.text((the_x + 2, 82), the_text, font=font, fill=(0, 0, 0))
        draw.text((the_x, 80), the_text, font=font, fill=(255, 255, 255))

        # Add "VALERIES" text
        val_text = "VALERIES"
        val_bbox = draw.textbbox((0, 0), val_text, font=font)
        val_width = val_bbox[2] - val_bbox[0]
        val_x = (240 - val_width) // 2

        # Add shadow for "VALERIES"
        draw.text((val_x + 2, 122), val_text, font=font, fill=(0, 0, 0))
        draw.text((val_x, 120), val_text, font=font, fill=(255, 255, 255))

        return sleep_image

    except Exception as e:
        print(f"Error creating sleep screen: {e}")
        # Fallback to dark red screen with text
        sleep_image = Image.new('RGB', (240, 240), (40, 0, 0))
        draw = ImageDraw.Draw(sleep_image)
        draw.text((80, 110), "THE VALERIES", fill=(255, 255, 255))
        return sleep_image

def check_sleep_mode():
    """Check if player should enter sleep mode"""
    global is_sleeping, last_activity_time

    if not is_sleeping and time() - last_activity_time > SLEEP_TIMEOUT:
        print("Entering sleep mode...")
        sleep_image = create_sleep_screen()
        disp.display(sleep_image.convert('RGB'))
        is_sleeping = True

def update_activity():
    """Reset the activity timer"""
    global last_activity_time, is_sleeping
    last_activity_time = time()
    is_sleeping = False

def get_fire_color(height_percent):
    """Generate a color in the fire spectrum based on height percentage"""
    if height_percent < 0.2:
        return (min(255, int(height_percent * 5 * 255)), 0, 0, 230)
    elif height_percent < 0.4:
        return (255, int((height_percent - 0.2) * 5 * 255), 0, 230)
    elif height_percent < 0.6:
        return (255, 255, int((height_percent - 0.4) * 5 * 255), 230)
    else:
        intensity = int((height_percent - 0.6) * 2.5 * 255)
        return (255, 255, min(255, 128 + intensity), 230)

def update_visualization():
    """Update the visualization heights based on playback status"""
    global viz_heights, viz_targets

    if playing and pygame.mixer.music.get_busy():
        for i in range(viz_bars):
            if random.random() < 0.3:
                viz_targets[i] = random.uniform(0.3, 1.0)
            diff = viz_targets[i] - viz_heights[i]
            viz_heights[i] += diff * viz_speed
    else:
        for i in range(viz_bars):
            viz_heights[i] = max(0, viz_heights[i] - 0.05)
            viz_targets[i] = 0

def draw_scrolling_text(draw, text, x, y, font, fill_color, shadow_color):
    """Draw scrolling text with shadow effect"""
    global scroll_position, scroll_pause_counter

    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]

    if text_width > SCROLL_WIDTH:
        if scroll_pause_counter > 0:
            scroll_pause_counter -= 1
            effective_pos = 0
        else:
            effective_pos = -scroll_position
            scroll_position += scroll_speed
            if scroll_position > text_width + 20:
                scroll_position = 0
                scroll_pause_counter = scroll_pause

        # Draw shadow
        draw.text((x + 2 + effective_pos, y + 2), text, font=font, fill=shadow_color)
        # Draw text
        draw.text((x + effective_pos, y), text, font=font, fill=fill_color)
    else:
        # Center non-scrolling text
        x = x + (SCROLL_WIDTH - text_width) // 2
        # Draw shadow
        draw.text((x + 2, y + 2), text, font=font, fill=shadow_color)
        # Draw text
        draw.text((x, y), text, font=font, fill=fill_color)

def create_gothic_display():
    """Create the display with crystal red theme and fire effects"""
    width, height = 240, 240
    image = Image.new('RGBA', (width, height), COLORS['background'])
    draw = ImageDraw.Draw(image)

    # Add crystal gradient overlay at the bottom
    for y in range(height - 100, height):
        opacity = int((y - (height - 100)) / 100 * 160)
        draw.line([(0, y), (width, y)], fill=(80, 0, 0, opacity))

    # Load fonts
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
                                      FONT_SIZES['title'])
        info_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
                                     FONT_SIZES['info'])
    except:
        title_font = info_font = ImageFont.load_default()

    # Draw track information
    if songs:
        # Track number
        track_text = f"Track {current_track + 1}/{len(songs)}"
        draw.text((22, 32), track_text, font=info_font, fill=COLORS['shadow'])
        draw.text((20, 30), track_text, font=info_font, fill=COLORS['glow'])

        # Scrolling song name
        song_name = os.path.splitext(os.path.basename(songs[current_track]))[0]
        draw_scrolling_text(draw, song_name, 20, 60, title_font, COLORS['text'], COLORS['shadow'])

        # Status and volume
        status_text = "▶ Playing" if playing else "❚❚ Paused"
        draw.text((20, 100), status_text, font=info_font,
                 fill=COLORS['glow'] if playing else COLORS['text'])

        vol_text = f"Volume: {int(volume * 100)}%"
        draw.text((20, 130), vol_text, font=info_font, fill=COLORS['crystal'])
    else:
        draw.text((20, 100), "No music files found", font=title_font, fill=COLORS['text'])
        draw.text((20, 140), f"in {MUSIC_DIR}", font=info_font, fill=COLORS['text'])

    # Draw reactive visualization bars with fire effect at the bottom
    update_visualization()
    bar_width = (width - 40) // viz_bars
    bar_spacing = 4
    max_bar_height = 60  # Reduced height for bottom placement
    base_y = height - 10  # Move bars to bottom

    for i in range(viz_bars):
        bar_height = int(viz_heights[i] * max_bar_height)
        if bar_height > 0:
            x = 20 + i * (bar_width + bar_spacing)
            for h in range(bar_height):
                height_percent = h / max_bar_height
                color = get_fire_color(height_percent)
                draw.line([(x, base_y - h), (x + bar_width - bar_spacing, base_y - h)], fill=color)

                if h == bar_height - 1 and random.random() < 0.3:
                    flicker_height = random.randint(2, 5)
                    for fh in range(flicker_height):
                        flicker_color = get_fire_color(min(1.0, height_percent + 0.2))
                        if random.random() < 0.7:
                            draw.line([(x, base_y - h - fh),
                                     (x + bar_width - bar_spacing, base_y - h - fh)],
                                    fill=flicker_color)

    return image

def play_song():
    """Play the current song"""
    global playing, error_count
    if songs:
        try:
            pygame.mixer.music.load(songs[current_track])
            pygame.mixer.music.play()
            pygame.mixer.music.set_volume(volume)
            playing = True
            error_count = 0
            print(f"Playing: {songs[current_track]}")
        except Exception as e:
            print(f"Error playing {songs[current_track]}: {e}")
            try_next_song()

def try_next_song():
    """Try to play the next song if current one fails"""
    global current_track, error_count
    if error_count >= len(songs):
        error_count = 0
        return False
    current_track = (current_track + 1) % len(songs)
    error_count += 1
    play_song()
    return True

def adjust_volume(change):
    """Adjust the volume by the given amount"""
    global volume
    volume = max(0.0, min(1.0, volume + change))
    pygame.mixer.music.set_volume(volume)

def force_sleep_mode():
    """Force the player into sleep mode"""
    global is_sleeping
    logging.info("Forcing sleep mode...")
    is_sleeping = True
    sleep_image = create_sleep_screen()
    disp.display(sleep_image.convert('RGB'))

def update_display():
    """Update the display with current information"""
    image = create_gothic_display()
    disp.display(image.convert('RGB'))

def cleanup():
    """Clean up resources and turn off display"""
    try:
        # Create sleep screen for final display
        final_image = create_sleep_screen()
        disp.display(final_image.convert('RGB'))
    except Exception as e:
        print(f"Error during cleanup: {e}")
        final_image = Image.new('RGB', (240, 240), (80, 0, 0))
        disp.display(final_image)

    GPIO.cleanup()
    pygame.mixer.quit()

# Initialize pygame mixer
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
pygame.mixer.music.set_volume(volume)

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup([BUTTON_A, BUTTON_B, BUTTON_X, BUTTON_Y], GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Main program loop
try:
    print("Initializing music player...")
    load_songs()

    print("Initializing display...")
    update_display()
    update_activity()  # Initialize activity timer

    last_check_time = time()
    print("Starting main loop...")

    while True:
        current_time = time()

        # Update visualization if playing
        if playing and not is_sleeping:
            update_visualization()
            update_display()
            sleep(0.05)  # Faster updates for smooth visualization

        # Check for sleep mode
        if not is_sleeping:
            check_sleep_mode()
            # Force sleep mode: Y + B combination
            if not GPIO.input(BUTTON_Y) and not GPIO.input(BUTTON_B):
                force_sleep_mode()
                sleep(0.2)  # Debounce
                continue  # Skip other button checks

            # Volume controls with Y as modifier
            elif not GPIO.input(BUTTON_Y):  # Y is held down
                update_activity()  # Reset sleep timer
                if not GPIO.input(BUTTON_A):  # Y + A for volume down
                    adjust_volume(-0.05)
                    update_display()
                    sleep(0.2)
                elif not GPIO.input(BUTTON_X):  # Y + X for volume up
                    adjust_volume(0.05)
                    update_display()
                    sleep(0.2)

            # Previous track: A
            elif not GPIO.input(BUTTON_A):
                update_activity()  # Reset sleep timer
                if songs:
                    current_track = (current_track - 1) % len(songs)
                    if playing:
                        play_song()
                    scroll_position = 0  # Reset scroll position for new track
                    update_display()
                    sleep(0.2)

            # Play/Pause: B
            elif not GPIO.input(BUTTON_B):
                update_activity()  # Reset sleep timer
                if songs:
                    if playing:
                        pygame.mixer.music.pause()
                        playing = False
                    else:
                        if not pygame.mixer.music.get_busy():
                            play_song()
                        else:
                            pygame.mixer.music.unpause()
                            playing = True
                    update_display()
                sleep(0.2)

            # Next track: X
            elif not GPIO.input(BUTTON_X):
                update_activity()  # Reset sleep timer
                if songs:
                    current_track = (current_track + 1) % len(songs)
                    if playing:
                        play_song()
                    scroll_position = 0  # Reset scroll position for new track
                    update_display()
                sleep(0.2)

            # Check for end of track
            if playing and not pygame.mixer.music.get_busy() and (current_time - last_check_time) >= 1.0:
                current_track = (current_track + 1) % len(songs)
                play_song()
                scroll_position = 0  # Reset scroll position for new track
                update_display()
                last_check_time = current_time

            if not playing:
                sleep(0.1)  # Slower updates when not playing

        else:  # In sleep mode
            # Only check for B button to wake up
            if not GPIO.input(BUTTON_B):
                logging.info("Waking from sleep mode via B button...")
                update_activity()  # Reset sleep timer
                update_display()  # Refresh display
                sleep(0.2)  # Debounce
            else:
                sleep(0.1)  # Reduce CPU usage in sleep mode

except KeyboardInterrupt:
    print("\nShutting down music player...")
    cleanup()
except Exception as e:
    print(f"Unexpected error: {e}")
    cleanup()
finally:
    print("Goodbye!")
