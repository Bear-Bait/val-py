# val-py

A music player for Raspberry Pi using the Pirate Audio Line Out HAT, featuring a crystal red theme inspired by [The Valeries](https://expatpress.com/product/the-valeries-forrest-muelrath/) (ExPat Press, 2024), with four audio files related to the story. 

![ValPlayer on Raspberry Pi](valpy-pi.png)

## Hardware Requirements
- Raspberry Pi 3 (or newer)
- Pirate Audio Line Out HAT
- USB storage device for music (optional)

## Software Requirements
- Python 3.7 or newer
- Debian Bookworm or similar. 

## Installation

1. Set up Raspberry Pi OS:
```bash
# Enable SPI interface
sudo raspi-config
# Navigate to Interface Options > SPI > Enable

# Install required packages
sudo apt update
sudo apt install -y python3-pip python3-pygame music player for Raspberry Pi using the Pirate Audio Line Out HAT, featuring a theme from the novel The Valeries, ExPat Press 2024, and four audio files that relate to the plot. 

## Hardware Requirements
- Raspberry Pi 3 (or newer)
- Pirate Audio Line Out HAT
- USB storage device for music (optional)

## Installation

1. Set up Raspberry Pi OS:
```bash
# Enable SPI interface
sudo raspi-config
# Navigate to Interface Options > SPI > Enable

# Install required packages
sudo apt update
sudo apt install -y python3-pip python3-pygame
```

2. Install Python dependencies:
```bash
sudo pip3 install st7789
```

3. Clone this repository:
```bash
git clone https://github.com/Bear-Bait/valplayer.git
cd valplayer
```

4. Copy music files:
- Primary location: `/media/usb/Music/`
- Fallback location: `~/Music/`

5. Run the player:
```bash
python3 val.py
```

## Controls
- **A**: Previous track
- **B**: Play/Pause
- **X**: Next track
- **Y + A**: Volume down ta
- **Y + X**: Volume up
- **Y + B**: Force sleep mode
- **B** (during sleep): Wake from sleep

## Features
- Automatic USB music detection with fallback to local directory
- Scrolling track names
- Fire-effect visualizations
- Sleep mode with customizable timeout
- Volume control
- Error handling for corrupt/missing files

## File Structure
- `val.py`: Main player script
- `valpy.png`: Logo for sleep mode display
