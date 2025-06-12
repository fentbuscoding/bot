# Music System for BronxBot

This music system provides comprehensive audio playback functionality for Discord servers.

## Features

### Core Commands (`core.py`)
- `.join` / `.connect` - Join your voice channel
- `.disconnect` / `.leave` / `.dc` - Leave voice channel
- `.play <song>` / `.p <song>` - Play a song from YouTube
- `.pause` - Pause current song
- `.resume` - Resume paused song
- `.skip` / `.next` - Skip current song
- `.stop` - Stop music and clear queue

### Queue Management (`queue.py`)
- `.queue` / `.q` - Interactive queue display with controls
- `.remove <#>` - Remove song from queue by position
- `.move <from> <to>` - Move song positions in queue
- `.shuffle` - Shuffle the queue
- `.clear` - Clear the entire queue
- `.nowplaying` / `.np` - Show current song info

### Advanced Player (`player.py`)
- `.search <query>` - Search YouTube and display results
- `.volume <0-100>` - Set playback volume
- `.playinfo` / `.info` - Detailed current song information
- `.lyrics [song]` - Get lyrics (placeholder for future implementation)

### Music Controls (`controls.py`)
- `.controls` / `.panel` - Interactive control panel
- `.loop <off/song/queue>` - Set loop modes
- `.autoplay <on/off>` - Auto-play related songs
- `.repeat` - Add current song back to queue
- `.skipto <#>` - Skip to specific queue position
- `.replay` / `.restart` - Restart current song

## Interactive Features

### Queue View
The queue command provides an interactive interface with:
- **Pagination** - Browse through long queues
- **Real-time controls** - Clear, shuffle, and refresh
- **Detailed info** - Duration, requester, and total time

### Control Panel
The controls command shows a comprehensive control panel with:
- **Play/Pause toggle**
- **Skip and Stop buttons**
- **Quick queue access**
- **Shuffle functionality**

## Permissions

Some commands require **Manage Messages** permission:
- Queue manipulation (clear, shuffle, remove, move)
- Volume above 50%
- Stop command
- Skip to position

## Technical Details

### Dependencies
- `yt-dlp` - YouTube video/audio extraction
- `PyNaCl` - Voice functionality for discord.py
- `discord.py` - Discord API wrapper

### Architecture
The music system is modular:

1. **Core Module** - Basic playback and voice management
2. **Queue Module** - Queue management and interactive displays
3. **Player Module** - Advanced audio handling and source management
4. **Controls Module** - Enhanced controls, loops, and user interactions

### Audio Quality
- Format: Best audio available from YouTube
- Volume: Adjustable 0-100% (default 50%)
- Reconnection: Automatic stream reconnection on network issues

## Usage Examples

```
# Basic usage
.join
.play never gonna give you up
.queue

# Advanced usage
.search bohemian rhapsody
.loop song
.volume 75
.controls

# Queue management
.shuffle
.remove 3
.move 1 5
.skipto 2
```

## Notes

- The bot must be in a voice channel to play music
- Users must be in the same voice channel as the bot
- Some features require specific permissions
- The system automatically handles queue progression
- Interactive elements have 5-minute timeouts

## Future Enhancements

- Lyrics integration with external APIs
- Playlist support
- Music recommendations
- Audio filters and effects
- Custom command aliases
- Voting systems for song management
