# ==========================================
# Captions Downloader 
# Version: 1.8.0
# Citation: Pundir, V. (2026, July 26). Captions Downloader Version (1.8.0). Retrieved from https://github.com/accidentalscholar/captions-downloader. 
# Citation: RIS and BibTeX files included for referencing software.
# Tested in: Python 3.10.9 64 bit packaged by Anaconda, Inc.
# Reporsitory: https://github.com/accidentalscholar/captions-downloader
# Provided under: GNU AFFERO GENERAL PUBLIC LICENSE (see accompanying license file)
# ==========================================

import sys
import os
import subprocess
import threading
import queue
import re
import glob
import urllib.request
import urllib.parse
import json
import html

# ------------------------------------------------------------------------------
# 1. Path Management
# Check for path.txt and append custom paths to sys.path if they exist.
# ------------------------------------------------------------------------------
path_file = "path.txt"
if os.path.exists(path_file):
    try:
        with open(path_file, "r") as f:
            for line in f:
                custom_path = line.strip()
                if custom_path and os.path.exists(custom_path):
                    sys.path.append(custom_path)
                    print(f"[INFO] Added custom path from {path_file}: {custom_path}")
    except Exception as e:
        print(f"[WARNING] Could not read {path_file}: {e}")

# ------------------------------------------------------------------------------
# 2. Dependency Management
# Ensure required dependencies are available, attempt install if missing.
# ------------------------------------------------------------------------------
REQUIRED_PACKAGES = {
    'yt_dlp': 'yt-dlp'
}

failed_installs = []

for module_name, pip_name in REQUIRED_PACKAGES.items():
    try:
        __import__(module_name)
    except ImportError:
        print(f"[INFO] Missing dependency '{pip_name}'. Attempting to install...")
        try:
            # Try installing via pip silently
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
            print(f"[SUCCESS] Successfully installed {pip_name}.")
        except subprocess.CalledProcessError:
            failed_installs.append(pip_name)
        except Exception as e:
            failed_installs.append(pip_name)
            print(f"[ERROR] Unexpected error during installation of {pip_name}: {e}")

# If any dependencies failed to install, exit gracefully and provide commands.
if failed_installs:
    error_msg = (
        "\n" + "="*60 + "\n"
        "ERROR: Required dependencies could not be automatically installed.\n"
        "Please open your terminal or Anaconda/Spyder prompt and run the\n"
        "following command(s) manually:\n\n"
    )
    for pkg in failed_installs:
        error_msg += f"    pip install {pkg}\n"
    
    error_msg += "\nAfter installing, restart the script.\n"
    error_msg += "="*60 + "\n"
    
    print(error_msg)
    sys.exit(1)

# Now it is safe to import yt_dlp and GUI components
import yt_dlp
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

# ------------------------------------------------------------------------------
# 3. Subtitle Processing & Thread-Safe Logging
# ------------------------------------------------------------------------------
class UIDownloadLogger:
    """
    Custom logger for yt-dlp to route messages to our Thread-Safe Queue.
    """
    def __init__(self, log_queue):
        self.log_queue = log_queue

    def debug(self, msg):
        # yt-dlp sends standard informational messages to debug
        if "Downloading subtitle" in msg or "Writing video subtitles" in msg or "Downloading playlist" in msg or "Skipping" in msg:
            self.log_queue.put(("LOG", msg))

    def info(self, msg):
        self.log_queue.put(("LOG", msg))

    def warning(self, msg):
        self.log_queue.put(("LOG", f"[WARNING] {msg}"))

    def error(self, msg):
        self.log_queue.put(("LOG", f"[ERROR] {msg}"))

def convert_subtitle_to_txt(filepath, log_queue):
    """
    Reads a .vtt or .srt file, strips timestamps and tags, deduplicates 
    scrolling text, unwraps sentence breaks into paragraphs, and creates a clean .txt file.
    """
    txt_filepath = filepath.rsplit('.', 1)[0] + ".txt"
    # Ensure we don't accidentally overwrite an already processed file if ran twice
    if filepath.endswith('.txt'):
        return

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove WEBVTT headers and metadata
        content = re.sub(r'WEBVTT.*?\n', '', content, flags=re.IGNORECASE)
        content = re.sub(r'Kind: captions.*?\n', '', content, flags=re.IGNORECASE)
        content = re.sub(r'Language:.*?\n', '', content, flags=re.IGNORECASE)
        content = re.sub(r'Position:.*?\n', '', content, flags=re.IGNORECASE)
        
        # Remove timestamps: 00:00:00.000 --> 00:00:00.000 or 00:00:00,000 --> 00:00:00,000
        content = re.sub(r'\d{2}:\d{2}:\d{2}[\.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[\.,]\d{3}.*\n?', '', content)
        # Remove short timestamps: 00:00.000 --> 00:00.000
        content = re.sub(r'\d{2}:\d{2}[\.,]\d{3}\s*-->\s*\d{2}:\d{2}[\.,]\d{3}.*\n?', '', content)
        
        # Remove standalone digits (SRT index numbers)
        content = re.sub(r'(?m)^\d+$\n?', '', content)
        
        # Remove HTML/XML-like styling tags and inline timestamps (e.g. <c.colorE5E5E5>, <i>, <00:00:00.320>)
        content = re.sub(r'<[^>]+>', '', content)
        
        # Split into individual lines to handle scrolling caption deduplication
        raw_lines = content.split('\n')
        cleaned_lines = []
        
        for line in raw_lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Deduplicate: YouTube rolling captions repeat the exact same text lines.
            # If the current line is exactly the same as the last line added, skip it.
            if cleaned_lines and cleaned_lines[-1] == line:
                continue
                
            cleaned_lines.append(line)

        merged_text = ""
        for line in cleaned_lines:
            if not merged_text:
                merged_text = line
            else:
                # If the previous line ends with a sentence terminator (. ! ?) 
                # or the new line indicates a change in speaker (- or >>), force a newline.
                # Otherwise, replace the line break with a single space.
                if re.search(r'[.!?]["\']?$', merged_text) or line.startswith('- ') or line.startswith('>>'):
                    merged_text += "\n" + line
                else:
                    merged_text += " " + line

        final_content = merged_text

        with open(txt_filepath, 'w', encoding='utf-8') as f:
            f.write(final_content)
            
        log_queue.put(("LOG", f"[SUCCESS] Converted and formatted: {os.path.basename(txt_filepath)}"))
    except Exception as e:
        log_queue.put(("LOG", f"[WARNING] Failed to clean {os.path.basename(filepath)}: {e}"))

# ------------------------------------------------------------------------------
# 4. GUI Application Definition
# ------------------------------------------------------------------------------
class SubtitleDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Subtitle/Transcript Downloader v1.8.0")
        self.root.geometry("700x480")
        
        self.is_destroyed = False
        self.log_queue = queue.Queue()

        # Handle window closure gracefully (crucial for Spyder compatibility)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Ensure window is in the foreground upon launch
        self.root.attributes('-topmost', True)
        self.root.update()
        self.root.after(500, lambda: self.root.attributes('-topmost', False))
        self.root.lift()

        # Build UI Elements
        self._build_ui()
        
        # Start the queue polling loop (Thread-safe way to update UI)
        self.root.after(100, self.process_queue)

    def _build_ui(self):
        """Constructs the Tkinter UI layout."""
        pad_options = {'padx': 10, 'pady': 5}

        # URL Frame
        url_frame = tk.Frame(self.root)
        url_frame.pack(fill=tk.X, **pad_options)
        
        tk.Label(url_frame, text="URL (Spotify/YouTube/Apple):", width=25, anchor='w').pack(side=tk.LEFT)
        self.url_entry = tk.Entry(url_frame)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Output Directory Frame
        dir_frame = tk.Frame(self.root)
        dir_frame.pack(fill=tk.X, **pad_options)
        
        tk.Label(dir_frame, text="Output Folder:", width=25, anchor='w').pack(side=tk.LEFT)
        self.dir_entry = tk.Entry(dir_frame)
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        browse_btn = tk.Button(dir_frame, text="Browse", command=self.browse_folder)
        browse_btn.pack(side=tk.LEFT, padx=(5, 0))

        # Options Frame
        options_frame = tk.Frame(self.root)
        options_frame.pack(fill=tk.X, **pad_options)
        
        tk.Label(options_frame, text="Settings:", width=25, anchor='w').pack(side=tk.LEFT)
        
        self.download_shorts_var = tk.BooleanVar(value=False)
        self.shorts_chk = tk.Checkbutton(options_frame, text="Download Shorts", variable=self.download_shorts_var)
        self.shorts_chk.pack(side=tk.LEFT)

        self.chronological_var = tk.BooleanVar(value=True)
        self.chrono_chk = tk.Checkbutton(options_frame, text="Process Oldest First (Reverse Playlist)", variable=self.chronological_var)
        self.chrono_chk.pack(side=tk.LEFT, padx=(10, 0))

        # Action Buttons Frame
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.download_btn = tk.Button(btn_frame, text="Start Download", command=self.start_download, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.download_btn.pack(side=tk.TOP, ipadx=10, ipady=5)

        # Status/Log Area
        log_frame = tk.Frame(self.root)
        log_frame.pack(fill=tk.BOTH, expand=True, **pad_options)
        
        tk.Label(log_frame, text="Process Log:", anchor='w').pack(fill=tk.X)
        self.log_area = scrolledtext.ScrolledText(log_frame, height=10, state=tk.DISABLED, bg="#f4f4f4")
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def browse_folder(self):
        """Opens a folder selection dialog and updates the entry."""
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, folder_selected)

    def process_queue(self):
        """Polls the queue for messages from the background thread and updates the UI."""
        try:
            while True:
                msg_type, msg_data = self.log_queue.get_nowait()
                
                if msg_type == "LOG":
                    self.log_area.config(state=tk.NORMAL)
                    self.log_area.insert(tk.END, msg_data + "\n")
                    self.log_area.see(tk.END)
                    self.log_area.config(state=tk.DISABLED)
                elif msg_type == "STATE":
                    downloading = msg_data
                    state = tk.DISABLED if downloading else tk.NORMAL
                    self.url_entry.config(state=state)
                    self.dir_entry.config(state=state)
                    self.shorts_chk.config(state=state)
                    self.chrono_chk.config(state=state)
                    self.download_btn.config(state=state)
                    
                    if downloading:
                        self.download_btn.config(text="Downloading...", bg="#888888")
                    else:
                        self.download_btn.config(text="Start Download", bg="#4CAF50")
                elif msg_type == "CLOSE":
                    # Wait 2 seconds before closing so user can read the success message
                    self.root.after(2000, self.on_closing)
                        
        except queue.Empty:
            pass
        finally:
            if not self.is_destroyed:
                self.root.after(100, self.process_queue)

    def on_closing(self):
        """Handles closing the application cleanly to prevent Spyder crashes."""
        self.is_destroyed = True
        self.root.quit()
        self.root.destroy()

    def start_download(self):
        """Initiates the download process in a separate thread."""
        url = self.url_entry.get().strip()
        output_folder = self.dir_entry.get().strip()
        download_shorts = self.download_shorts_var.get()
        chronological = self.chronological_var.get()

        if not url:
            messagebox.showwarning("Input Error", "Please provide a valid URL.")
            return
        if not output_folder or not os.path.isdir(output_folder):
            messagebox.showwarning("Input Error", "Please select a valid output folder.")
            return

        self.log_queue.put(("STATE", True))
        
        # Clear log area
        self.log_area.config(state=tk.NORMAL)
        self.log_area.delete('1.0', tk.END)
        self.log_area.config(state=tk.DISABLED)
        
        self.log_queue.put(("LOG", f"Starting job for URL: {url}"))
        self.log_queue.put(("LOG", f"Target directory: {output_folder}"))
        
        if "spotify.com" in url.lower():
             self.log_queue.put(("LOG", f"[WARNING] Spotify often uses aggressive DRM which blocks transcript extraction. yt-dlp may fail to fetch them."))

        if not download_shorts:
            self.log_queue.put(("LOG", f"Settings: Shorts filtering ENABLED (Shorts will be skipped)"))
        if chronological:
            self.log_queue.put(("LOG", f"Settings: Processing Playlist/Channel Oldest First"))
        self.log_queue.put(("LOG", "-" * 50))

        # Run in a background thread to prevent Tkinter freezing
        thread = threading.Thread(target=self._process_download, args=(url, output_folder, download_shorts, chronological))
        thread.daemon = True
        thread.start()

    def _find_alternatives(self, url):
        """
        Attempts to scrape the show title from a failed URL (Spotify/Apple)
        and searches for alternatives on other platforms.
        """
        self.log_queue.put(("LOG", "[INFO] Attempting to find alternative sources..."))
        title = "Unknown Show"
        
        # 1. Scrape Page for Show Title
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            html_content = urllib.request.urlopen(req).read().decode('utf-8')
            match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
            if match:
                title = match.group(1)
                title = html.unescape(title)
                
                # Clean up generic Spotify title tags
                title = re.sub(r'(?i)\s*\|\s*Podcast on Spotify$', '', title)
                title = re.sub(r'(?i)\s*-\s*Podcast on Spotify$', '', title)
                title = re.sub(r'(?i)\s*\|\s*Spotify$', '', title)
                
                # Clean up generic Apple Podcast tags
                title = re.sub(r'(?i)\s*on Apple Podcasts$', '', title)
                title = re.sub(r'\u200e', '', title) # Remove left-to-right invisible marks
                
                title = title.strip()
        except Exception as e:
            self.log_queue.put(("LOG", f"[WARNING] Could not extract title from page: {e}"))
            return False
            
        self.log_queue.put(("LOG", f"[INFO] Identified show name: '{title}'"))
        
        apple_url = None
        # 2. Search Apple Podcasts using public iTunes API (only if not already an Apple URL)
        if "apple.com" not in url.lower():
            try:
                query = urllib.parse.quote(title)
                itunes_api = f"https://itunes.apple.com/search?term={query}&entity=podcast&limit=1"
                req = urllib.request.Request(itunes_api, headers={'User-Agent': 'Mozilla/5.0'})
                response = urllib.request.urlopen(req).read().decode('utf-8')
                data = json.loads(response)
                if data['resultCount'] > 0:
                    apple_url = data['results'][0].get('collectionViewUrl')
            except Exception as e:
                self.log_queue.put(("LOG", f"[WARNING] iTunes Search failed: {e}"))
                
        # 3. Formulate a general YouTube search query link
        yt_query = urllib.parse.quote(f"{title} podcast")
        yt_url = f"https://www.youtube.com/results?search_query={yt_query}"
        
        # Output Suggestions
        self.log_queue.put(("LOG", "\n" + "=" * 50))
        self.log_queue.put(("LOG", "[SUGGESTION] Could not download subtitles from the provided URL."))
        self.log_queue.put(("LOG", "Try downloading from these alternative links instead:"))
        if apple_url:
            self.log_queue.put(("LOG", f"\nAPPLE PODCASTS: {apple_url}"))
        self.log_queue.put(("LOG", f"\nYOUTUBE SEARCH: {yt_url}"))
        self.log_queue.put(("LOG", "=" * 50 + "\n"))
        
        return True

    def _process_download(self, url, output_folder, download_shorts, chronological):
        """
        Background task that interfaces with yt-dlp to download subtitles, 
        and then cleans up filenames and converts them.
        """
        def filter_shorts(info, *, incomplete):
            """Internal filter to skip shorts based on URL patterns."""
            url_str = info.get('url', '')
            webpage_url_str = info.get('webpage_url', '')
            original_url_str = info.get('original_url', '')
            
            # Check if '/shorts/' is in any of the resolved URLs
            for u in (url_str, webpage_url_str, original_url_str):
                if u and '/shorts/' in u:
                    return 'Skipping Short video (disabled in settings)'
            return None

        # Configure yt-dlp parameters
        # %(playlist_autonumber,episode_number|)s evaluates to either the playlist index (001, 002) 
        # or the spotify/apple episode number (45). If neither exists, it defaults to empty string.
        ydl_opts = {
            'skip_download': True,              # We only want subs/captions, no media
            'writesubtitles': True,             # Write manually uploaded subtitles
            'writeautomaticsub': True,          # Fallback to auto-generated transcripts
            'subtitleslangs': ['en', 'en-US', 'en-GB', 'en.*'], # Target English variants
            'outtmpl': os.path.join(output_folder, '%(playlist_autonumber,episode_number|)s_%(title)s_%(id)s.%(ext)s'),
            'ignoreerrors': True,               # Continue if a channel video is unavailable/private
            'allow_unplayable_formats': True,   # Try to bypass DRM errors for metadata/subs extraction
            'ignore_no_formats_error': True,    # Prevents crashing if media cannot be decrypted
            'logger': UIDownloadLogger(self.log_queue),
            'extract_flat': False,              # Need to extract info to get subs
            'noplaylist': False,                # Ensure channels AND playlists iterate fully
            'playlistreverse': chronological,   # Reverses list to process Oldest -> Newest
        }
        
        # Inject the shorts filter if the user chose not to download shorts
        if not download_shorts:
            ydl_opts['match_filter'] = filter_shorts

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.log_queue.put(("LOG", "[INFO] Extracting metadata and downloading subtitles..."))
                ydl.download([url])
                
            self.log_queue.put(("LOG", "-" * 50))
            self.log_queue.put(("LOG", "[INFO] Scanning for downloaded subtitles to clean and convert..."))
            
            search_patterns = [
                os.path.join(output_folder, "*.vtt"),
                os.path.join(output_folder, "*.srt")
            ]
            
            converted_count = 0
            for pattern in search_patterns:
                for file_path in glob.glob(pattern):
                    # Clean up the leading underscore created by outtmpl if this was a single video
                    # (where episode_number and playlist_autonumber were missing)
                    dir_name, file_name = os.path.split(file_path)
                    if file_name.startswith('_'):
                        new_file_name = file_name[1:] # Strip just the first underscore
                        new_file_path = os.path.join(dir_name, new_file_name)
                        try:
                            # Avoid FileExistsError if single file downloaded repeatedly
                            if os.path.exists(new_file_path):
                                os.remove(new_file_path)
                            os.rename(file_path, new_file_path)
                            file_path = new_file_path  # Point to the new correct file path
                        except Exception as e:
                            self.log_queue.put(("LOG", f"[WARNING] Could not rename {file_name}: {e}"))
                    
                    # Convert to final TXT format
                    convert_subtitle_to_txt(file_path, self.log_queue)
                    converted_count += 1
                    
            if converted_count == 0:
                self.log_queue.put(("LOG", "[INFO] No subtitles found to convert."))
                
                # If no subtitles exist, offer alternatives (skip if already on YouTube)
                if "youtube.com" not in url.lower() and "youtu.be" not in url.lower():
                    triggered = self._find_alternatives(url)
                    if triggered:
                        self.log_queue.put(("LOG", "[INFO] Application will remain open so you can copy the links."))
                        return # Exit function early to prevent auto-close signal
                        
            else:
                self.log_queue.put(("LOG", "-" * 50))
                self.log_queue.put(("LOG", f"[SUCCESS] Converted {converted_count} files."))
                
            self.log_queue.put(("LOG", "-" * 50))
            self.log_queue.put(("LOG", "[SUCCESS] Process completed. Closing application in 2 seconds..."))
            
            # Send signal to close the application automatically
            self.log_queue.put(("CLOSE", None))
            
        except Exception as e:
            self.log_queue.put(("LOG", "-" * 50))
            self.log_queue.put(("LOG", f"[ERROR] A critical error occurred: {str(e)}"))
            
        finally:
            # Re-enable UI components
            self.log_queue.put(("STATE", False))

# ------------------------------------------------------------------------------
# 5. Application Entry Point
# ------------------------------------------------------------------------------
def main():
    root = tk.Tk()
    
    # Optional styling adjustments
    try:
        from tkinter import ttk
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass 

    app = SubtitleDownloaderApp(root)
    
    # Run the interactive loop safely
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.on_closing()

if __name__ == "__main__":
    main()