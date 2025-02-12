# PyHero

PyHero is a full-featured, rhythm-based game inspired by the classic Guitar Hero series. Built entirely in Python using PyGame and Librosa, the game allows you to load any custom song, automatically analyzes its beat structure, and generates synchronized falling notes with realistic visual effects. Choose your difficulty, read the guide for controls, and enjoy a unique take on the rhythm game experience!

## Features

- **Custom Song Support & Beat Detection**  
  Load any audio file (MP3, OGG, WAV) and have Librosa automatically analyze the beat structure to generate a note chart.

- **Realistic Guitar Neck Visuals**  
  The game displays a realistic, trapezoidal "guitar neck" background complete with antialiased string lines.

- **Dynamic Note Rendering**  
  Notes fall in perspective from the top of their respective lanes. Long notes feature glowing tails that brighten when held, and additional points are awarded continuously while holding a long note.

- **Interactive Menu System**  
  Navigate a complete menu system with clickable buttons and keyboard shortcuts:
  - **Start Game** – Begin gameplay.
  - **Difficulty** – Select from Easy, Medium, Hard, Extreme, or Chill (no limit).
  - **Guide** – Learn the controls with visual representations (colored circles).
  - **Quit** – Exit the game.

- **End-of-Song & Game Over Screens**  
  After the song ends or if you lose by missing too many notes, a screen shows your final score and offers options to restart, choose a new song, return to the main menu, or quit.

- **Audio & Visual Feedback**  
  Enjoy realistic hit effects, miss effects (with a sound effect if `miss.wav` is available), button depress animations, and flashy multiplier displays.

## How It Works

- **Beat Detection & Chart Generation:**  
  The game uses Librosa to analyze the selected song and detect beat timings. For each beat, a note is generated with:
  - A random lane (from five available lanes)
  - A random travel time (so notes fall at varying speeds)
  - A chance to be a long note (with a random duration)

- **Rendering & Gameplay:**  
  Using PyGame, the game draws a realistic guitar neck by interpolating between top and bottom lane positions. Notes are drawn with smooth, antialiased shapes (using `pygame.gfxdraw`) and fall in sync with the song. Long-note tails glow and brighten when the corresponding key is held, and real-time scoring is applied.

- **Menu & Interaction:**  
  The game features multiple menu screens (main menu, difficulty selection, guide, end screens) that support both mouse clicks and keyboard shortcuts. An arrow back button (and the ESC key) allows you to return to previous menus.

- **Difficulty Settings:**  
  Choose from five difficulty options:
  - **Easy:** 10 misses allowed
  - **Medium:** 6 misses allowed (default)
  - **Hard:** 3 misses allowed
  - **Extreme:** 0 misses allowed (any miss ends the game)
  - **Chill:** No miss limit (play until the song ends)

## Installation

Make sure you have Python 3 installed. Then, install the required Python packages using pip:

```bash
pip install pygame librosa
