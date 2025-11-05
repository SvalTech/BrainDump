import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import sqlite3
import os
import shutil
import datetime
import subprocess
import sys

# --- New Dependency Check ---
# Features require the Pillow library (PIL).
try:
    from PIL import ImageGrab, Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageTk = None

# Define the directory and database file
APP_DIR = os.path.join(os.path.expanduser('~'), 'BrainDumpApp')
DB_FILE = os.path.join(APP_DIR, 'braindump.db')
FILES_DIR = os.path.join(APP_DIR, 'files')

# --- NEW: UI Color Palette (Dark Mode) ---
BG_COLOR = '#2b2b2b'       # Dark gray background
FRAME_COLOR = '#3c3c3c'   # Lighter gray for content frames
TEXT_COLOR = '#dcdcdc'     # Light text
ACCENT_COLOR = '#4a90e2'   # A nice blue for buttons and highlights
LIGHT_TEXT = '#9a9a9a'     # Muted text for metadata
BORDER_COLOR = '#555555'    # Dark border color
ENTRY_BG = '#454545'      # Background for text entries
SELECTED_BG = '#555555'     # Background for selected/active items
CURSOR_COLOR = '#dcdcdc'    # Text cursor color

class BrainDumpApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Local Brain Dump")
        self.root.geometry("1000x750") # Increased size
        self.root.minsize(700, 600)
        self.root.configure(bg=BG_COLOR)
        
        # This will hold a reference to the displayed image to prevent garbage collection
        self.photo_image = None

        # Ensure database and directories exist
        self.setup_database()

        # --- Configure Styles (Dark Mode) ---
        self.style = ttk.Style()
        self.style.theme_use('clam') # 'clam' is a good base for customization

        # General styles
        self.style.configure('.',
            font=('Helvetica', 10),
            background=BG_COLOR,
            foreground=TEXT_COLOR,
            fieldbackground=ENTRY_BG,
            bordercolor=BORDER_COLOR,
            lightcolor=FRAME_COLOR,
            darkcolor=BG_COLOR
        )
        self.style.configure('TFrame', background=BG_COLOR)
        self.style.configure('TLabel', background=BG_COLOR, foreground=TEXT_COLOR)
        self.style.configure('Header.TLabel', font=('Helvetica', 16, 'bold'), background=BG_COLOR)
        self.style.configure('Meta.TLabel', font=('Helvetica', 9, 'italic'), foreground=LIGHT_TEXT, background=FRAME_COLOR)
        self.style.configure('Bold.TLabel', font=('Helvetica', 10, 'bold'), background=FRAME_COLOR)

        # Content Frame style
        self.style.configure('Content.TFrame', background=FRAME_COLOR, relief=tk.SOLID, borderwidth=1, bordercolor=BORDER_COLOR)

        # Button styles
        self.style.configure('TButton', font=('Helvetica', 10, 'bold'), padding=8, relief=tk.FLAT, borderwidth=0)
        self.style.map('TButton',
            background=[('!active', ACCENT_COLOR), ('active', '#5aa0eb')],
            foreground=[('!disabled', '#ffffff')])
        
        # Style for the "Paste" button
        self.style.configure('Paste.TButton', font=('Helvetica', 10, 'bold'), padding=8, relief=tk.FLAT, borderwidth=0)
        self.style.map('Paste.TButton',
            background=[('!active', '#28a745'), ('active', '#34c759')], # Green
            foreground=[('!disabled', '#ffffff')])

        # Entry widget
        self.style.configure('TEntry',
            font=('Helvetica', 10),
            padding=5,
            relief=tk.FLAT,
            borderwidth=1,
            fieldbackground=ENTRY_BG,
            foreground=TEXT_COLOR
        )
        self.style.map('TEntry',
            bordercolor=[('focus', ACCENT_COLOR), ('!focus', BORDER_COLOR)],
            fieldbackground=[('disabled', BG_COLOR)]
        )
        
        # --- Treeview (List) Style ---
        self.style.configure('Treeview',
            background=FRAME_COLOR,
            fieldbackground=FRAME_COLOR,
            foreground=TEXT_COLOR,
            rowheight=25,
            relief=tk.FLAT,
            borderwidth=0)
        self.style.map('Treeview',
            background=[('selected', ACCENT_COLOR)],
            foreground=[('selected', '#ffffff')]
        )
        self.style.configure('Treeview.Heading',
            font=('Helvetica', 10, 'bold'),
            padding=5,
            relief=tk.FLAT,
            background=SELECTED_BG,
            foreground=TEXT_COLOR
        )
        self.style.map('Treeview.Heading',
            background=[('!active', SELECTED_BG), ('active', FRAME_COLOR)],
            foreground=[('!active', TEXT_COLOR)]
        )

        # --- Main Layout ---
        self.main_frame = ttk.Frame(root, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.main_frame.rowconfigure(0, weight=3) # Input area
        self.main_frame.rowconfigure(1, weight=5) # Content list
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=2)

        # --- 1. Input Section (Top Left) ---
        self.input_frame = ttk.Frame(self.main_frame, padding=15, style='Content.TFrame')
        self.input_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 10), pady=(0, 10))
        self.input_frame.rowconfigure(1, weight=1) # Make text box expandable
        self.input_frame.columnconfigure(0, weight=1)

        ttk.Label(self.input_frame, text="Dump your thoughts, notes, or files...", style='Header.TLabel', background=FRAME_COLOR).grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky='w')
        
        self.note_text = scrolledtext.ScrolledText(
            self.input_frame, height=8, width=40, wrap=tk.WORD,
            font=('Helvetica', 10), relief=tk.FLAT, borderwidth=1, bd=1,
            highlightthickness=1, highlightcolor=BORDER_COLOR,
            bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=CURSOR_COLOR
        )
        self.note_text.grid(row=1, column=0, columnspan=2, sticky='nsew', pady=5)
        
        self.tag_frame = ttk.Frame(self.input_frame, style='Content.TFrame')
        self.tag_frame.grid(row=2, column=0, columnspan=2, sticky='ew', pady=5)
        ttk.Label(self.tag_frame, text="Tags (comma-separated):", background=FRAME_COLOR).pack(side=tk.LEFT, padx=(0, 5))
        self.tag_entry = ttk.Entry(self.tag_frame)
        self.tag_entry.pack(fill=tk.X, expand=True, side=tk.LEFT)
        
        self.button_frame = ttk.Frame(self.input_frame, style='Content.TFrame')
        self.button_frame.grid(row=3, column=0, columnspan=2, sticky='ew', pady=(5, 0))
        
        ttk.Button(self.button_frame, text="Save Note", command=self.add_note, style='TButton').pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(self.button_frame, text="Add File", command=self.add_file, style='TButton').pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        self.paste_button = ttk.Button(self.button_frame, text="Paste from Clipboard", command=self.paste_from_clipboard, style='Paste.TButton')
        self.paste_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        if not PIL_AVAILABLE:
            self.paste_button.config(state=tk.DISABLED, text="Paste (Needs Pillow)")
            self.paste_button.bind("<Enter>", lambda e: self.show_tooltip("Install 'Pillow' library to enable"))
            self.paste_button.bind("<Leave>", lambda e: self.hide_tooltip())
        self.tooltip = None

        # --- 2. Search & List Section (Bottom Left) ---
        self.list_frame = ttk.Frame(self.main_frame, padding=15, style='Content.TFrame')
        self.list_frame.grid(row=1, column=0, sticky='nsew', padx=(0, 10))
        self.list_frame.rowconfigure(3, weight=1) # Row 3 (tree_frame) will expand
        self.list_frame.columnconfigure(0, weight=1)

        # General Search
        self.search_frame = ttk.Frame(self.list_frame, style='Content.TFrame')
        self.search_frame.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 10))
        ttk.Label(self.search_frame, text="Search Content:", background=FRAME_COLOR).pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = ttk.Entry(self.search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.bind("<Return>", lambda e: self.load_entries())
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_entries())
        
        # --- NEW: Tag Filter ---
        self.tag_filter_frame = ttk.Frame(self.list_frame, style='Content.TFrame')
        self.tag_filter_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(0, 10))
        ttk.Label(self.tag_filter_frame, text="Filter by Tag:", background=FRAME_COLOR).pack(side=tk.LEFT, padx=(0, 5))
        self.tag_filter_entry = ttk.Entry(self.tag_filter_frame)
        self.tag_filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.tag_filter_entry.bind("<Return>", lambda e: self.load_entries())
        self.tag_filter_entry.bind("<KeyRelease>", lambda e: self.load_entries())


        # --- Treeview ---
        self.tree_frame = ttk.Frame(self.list_frame, style='Content.TFrame')
        self.tree_frame.grid(row=3, column=0, columnspan=2, sticky='nsew') # Changed row
        self.tree_scroll_y = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL)
        
        self.tree = ttk.Treeview(
            self.tree_frame,
            columns=('date', 'type', 'preview'),
            show='headings',
            yscrollcommand=self.tree_scroll_y.set
        )
        self.tree_scroll_y.config(command=self.tree.yview)

        self.tree.heading('date', text='Date', anchor='w')
        self.tree.heading('type', text='Type', anchor='w')
        self.tree.heading('preview', text='Preview', anchor='w')
        
        self.tree.column('date', stretch=False, width=110, anchor='w')
        self.tree.column('type', stretch=False, width=50, anchor='w')
        self.tree.column('preview', stretch=True, width=200, anchor='w')
        
        self.tree_frame.rowconfigure(0, weight=1)
        self.tree_frame.columnconfigure(0, weight=1)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        self.tree_scroll_y.grid(row=0, column=1, sticky='ns')
        
        self.tree.bind('<<TreeviewSelect>>', self.on_entry_select)
        
        # --- 3. Display Section (Right) ---
        # --- NEW: Re-architected with Canvas for scrolling ---
        self.display_frame = ttk.Frame(self.main_frame, style='Content.TFrame')
        self.display_frame.grid(row=0, column=1, rowspan=2, sticky='nsew', pady=(10, 0))
        self.display_frame.rowconfigure(0, weight=1)
        self.display_frame.columnconfigure(0, weight=1)

        # Create Canvas and Scrollbar
        self.display_canvas = tk.Canvas(self.display_frame, bg=FRAME_COLOR, highlightthickness=0, borderwidth=0)
        self.display_scrollbar = ttk.Scrollbar(self.display_frame, orient=tk.VERTICAL, command=self.display_canvas.yview)
        
        self.display_canvas.configure(yscrollcommand=self.display_scrollbar.set)
        
        # Grid them
        self.display_canvas.grid(row=0, column=0, sticky='nsew', padx=(15,0), pady=15)
        self.display_scrollbar.grid(row=0, column=1, sticky='ns', padx=(0,15), pady=15)
        
        # This frame holds the actual content and will be placed inside the canvas
        self.scrollable_content_frame = ttk.Frame(self.display_canvas, style='Content.TFrame')
        self.scrollable_content_frame.columnconfigure(0, weight=1) # Ensure content frame scales
        
        # Create the window in the canvas
        self.canvas_window = self.display_canvas.create_window((0, 0), window=self.scrollable_content_frame, anchor='nw')

        # Bind events for scrolling
        self.scrollable_content_frame.bind('<Configure>', self.on_frame_configure)
        self.display_canvas.bind('<Configure>', self.on_canvas_configure)
        
        # Bind mouse wheel scrolling
        self.display_canvas.bind_all("<MouseWheel>", self._on_mousewheel) # Windows/macOS
        self.display_canvas.bind_all("<Button-4>", self._on_mousewheel) # Linux
        self.display_canvas.bind_all("<Button-5>", self._on_mousewheel) # Linux

        self.show_welcome_message()
        self.load_entries()

    # --- NEW: Functions for scrollable frame ---
    def on_frame_configure(self, event):
        """Update the canvas scrollregion when the inner frame's size changes."""
        self.display_canvas.configure(scrollregion=self.display_canvas.bbox("all"))

    def on_canvas_configure(self, event):
        """Update the inner frame's width to match the canvas's width."""
        canvas_width = event.width
        self.display_canvas.itemconfig(self.canvas_window, width=canvas_width)

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        x, y = self.root.winfo_pointerxy()
        widget_under_cursor = self.root.winfo_containing(x, y)
        if not widget_under_cursor:
            return

        # Check if the widget is a descendant of the display_frame
        parent = widget_under_cursor
        while parent:
            if parent == self.display_frame:
                # Yes, scroll the canvas
                if sys.platform == "win32":
                    delta = -int(event.delta / 120)
                elif sys.platform == "darwin":
                    delta = event.delta
                else: # Linux
                    if event.num == 4:
                        delta = -1
                    else:
                        delta = 1
                
                self.display_canvas.yview_scroll(delta, "units")
                return # We handled it
            
            # Don't scroll the display_frame if we are over the list_frame
            if parent == self.list_frame:
                return # Let the list_frame's widgets handle it
                
            try:
                parent = parent.winfo_parent()
            except Exception:
                break
    # ---------------------------------------------

    def show_tooltip(self, text):
        if self.tooltip:
            self.tooltip.destroy()
        x, y, _, _ = self.paste_button.bbox("insert")
        x += self.paste_button.winfo_rootx() + 25
        y += self.paste_button.winfo_rooty() + 25
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip, text=text, background="#333", foreground="#fff", padx=5, pady=3, font=('Helvetica', 9))
        label.pack()

    def hide_tooltip(self):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
            
    def setup_database(self):
        """Creates the app directory, files directory, and SQLite database/table if they don't exist."""
        try:
            os.makedirs(APP_DIR, exist_ok=True)
            os.makedirs(FILES_DIR, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Error", f"Failed to create app directories: {e}")
            self.root.quit()
            
        try:
            self.conn = sqlite3.connect(DB_FILE)
            self.cursor = self.conn.cursor()
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT,
                    filepath TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # --- Add description column if it doesn't exist (for existing users) ---
            try:
                self.cursor.execute("ALTER TABLE entries ADD COLUMN description TEXT")
                self.conn.commit()
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e):
                    raise # Re-raise if it's not the error we expect
            
            self.conn.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to initialize database: {e}")
            self.root.quit()

    def add_note(self):
        """Saves a text note to the database."""
        content = self.note_text.get("1.0", tk.END).strip()
        tags = self.tag_entry.get().strip().lower()
        
        if not content:
            messagebox.showwarning("Empty Note", "Cannot save an empty note.")
            return
            
        try:
            self.cursor.execute(
                "INSERT INTO entries (type, content, tags) VALUES (?, ?, ?)",
                ('note', content, tags)
            )
            self.conn.commit()
            
            self.note_text.delete("1.0", tk.END)
            self.tag_entry.delete(0, tk.END)
            
            # messagebox.showinfo("Success", "Note saved!") # Less intrusive
            self.load_entries()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to save note: {e}")

    def add_file(self):
        """Saves a reference to a local file (e.g., screenshot) to the database."""
        filepath = filedialog.askopenfilename(title="Select a file to add")
        if not filepath:
            return
            
        tags = self.tag_entry.get().strip().lower()
        description = self.note_text.get("1.0", tk.END).strip()
        filename = os.path.basename(filepath)
        
        try:
            new_filepath = self.copy_file_to_storage(filepath, filename)
            if not new_filepath:
                return # Error was already shown

            self.cursor.execute(
                "INSERT INTO entries (type, content, tags, filepath, description) VALUES (?, ?, ?, ?, ?)",
                ('file', filename, tags, new_filepath, description) # Store base filename in content
            )
            self.conn.commit()
            
            self.note_text.delete("1.0", tk.END)
            self.tag_entry.delete(0, tk.END)
            # messagebox.showinfo("Success", "File added!") # Less intrusive
            self.load_entries()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to save file reference: {e}")

    def paste_from_clipboard(self):
        """
        Smarter paste function.
        1. Tries to paste an image.
        2. If no image, tries to see if the clipboard contains a path to an image file.
        3. If not, pastes the clipboard text into the note box.
        """
        if not PIL_AVAILABLE:
            messagebox.showerror("Feature Disabled", "This feature requires the 'Pillow' library.\n\nPlease install it using: pip install Pillow")
            return
        
        # 1. Try to get image data directly
        try:
            im = ImageGrab.grabclipboard()
        except Exception as e:
            im = None
            try:
                self.root.clipboard_get() # Test if clipboard has *anything*
            except tk.TclError:
                messagebox.showinfo("Clipboard Empty", "The clipboard is empty.")
                return
            except Exception as e_clip:
                messagebox.showerror("Clipboard Error", f"Could not read from clipboard: {e_clip}")
                return

        if im is not None and hasattr(im, 'save'):
            # --- SUCCESS: Found image data ---
            self.save_pasted_image_data(im)
            return

        # 2. No image data found. Check for text.
        clipboard_text = ""
        try:
            clipboard_text = self.root.clipboard_get()
        except tk.TclError:
            messagebox.showinfo("Clipboard Empty", "The clipboard is empty or does not contain text or a valid image.")
            return
        except Exception as e:
            messagebox.showerror("Clipboard Error", f"Could not read text from clipboard: {e}")
            return
            
        if not clipboard_text:
            messagebox.showinfo("Clipboard Empty", "The clipboard is empty.")
            return

        # 3. Check if the text is a valid file path to an image
        cleaned_path = clipboard_text.strip().strip('"')
        valid_image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
        
        if os.path.exists(cleaned_path) and os.path.isfile(cleaned_path) and cleaned_path.lower().endswith(valid_image_extensions):
            # --- SUCCESS: Found a file path to an image ---
            tags = self.tag_entry.get().strip().lower()
            description = self.note_text.get("1.0", tk.END).strip()
            filename = os.path.basename(cleaned_path)
            
            try:
                new_filepath = self.copy_file_to_storage(cleaned_path, filename)
                if not new_filepath:
                    return

                self.cursor.execute(
                    "INSERT INTO entries (type, content, tags, filepath, description) VALUES (?, ?, ?, ?, ?)",
                    ('file', filename, tags, new_filepath, description)
                )
                self.conn.commit()
                
                self.note_text.delete("1.0", tk.END)
                self.tag_entry.delete(0, tk.END)
                # messagebox.showinfo("Success", "Image file from clipboard path added!") # Less intrusive
                self.load_entries()
            except Exception as e:
                messagebox.showerror("Database Error", f"Failed to save file reference: {e}")
        else:
            # --- NOT an image, NOT a file path. Just paste the text. ---
            self.note_text.insert(tk.INSERT, clipboard_text)
            # messagebox.showinfo("Text Pasted", "Pasted text from clipboard into the note area.") # Less intrusive

    def save_pasted_image_data(self, im):
        """Helper function to save raw image data from clipboard."""
        tags = self.tag_entry.get().strip().lower()
        description = self.note_text.get("1.0", tk.END).strip()
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"paste_{timestamp}.png"
        new_filepath = os.path.join(FILES_DIR, filename)
        
        try:
            im.save(new_filepath, 'PNG')
        except Exception as e:
            messagebox.showerror("File Error", f"Failed to save pasted image: {e}")
            return

        try:
            self.cursor.execute(
                "INSERT INTO entries (type, content, tags, filepath, description) VALUES (?, ?, ?, ?, ?)",
                ('file', filename, tags, new_filepath, description)
            )
            self.conn.commit()
            
            self.note_text.delete("1.0", tk.END)
            self.tag_entry.delete(0, tk.END)
            # messagebox.showinfo("Success", "Pasted image saved as a new file!") # Less intrusive
            self.load_entries()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to save image reference: {e}")


    def copy_file_to_storage(self, filepath, filename):
        """Copies a file to the app's internal storage, handling conflicts."""
        try:
            new_filepath = os.path.join(FILES_DIR, filename)
            if os.path.exists(new_filepath):
                base, ext = os.path.splitext(filename)
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                new_filename = f"{base}_{timestamp}{ext}"
                new_filepath = os.path.join(FILES_DIR, new_filename)
                
            shutil.copy2(filepath, new_filepath)
            return new_filepath
        except Exception as e:
            messagebox.showerror("File Error", f"Failed to copy file: {e}")
            return None

    def load_entries(self):
        """Loads entries from the database into the Treeview, filtering by search."""
        search_term = self.search_entry.get().strip()
        # --- NEW: Get tag filter term ---
        tag_filter_term = self.tag_filter_entry.get().strip().lower()
        
        # Clear existing tree
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        try:
            # --- NEW: Dynamic query building ---
            base_query = "SELECT id, type, content, tags, timestamp FROM entries"
            where_clauses = []
            params = []
            
            if search_term:
                where_clauses.append("(content LIKE ? OR description LIKE ?)")
                params.extend([f"%{search_term}%", f"%{search_term}%"])
                
            if tag_filter_term:
                where_clauses.append("tags LIKE ?")
                params.append(f"%{tag_filter_term}%")
            
            if where_clauses:
                query = f"{base_query} WHERE {' AND '.join(where_clauses)} ORDER BY timestamp DESC"
            else:
                query = f"{base_query} ORDER BY timestamp DESC"
                
            self.cursor.execute(query, tuple(params))
                
            for row in self.cursor.fetchall():
                entry_id, type, content, tags, timestamp = row
                
                ts_date = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M')
                
                if type == 'note':
                    preview = content.split('\n')[0].replace('\r', '')[:50]
                    if len(content) > 50 or '\n' in content:
                        preview += "..."
                else: # 'file'
                    preview = content # Content is now the filename
                    
                self.tree.insert('', 'end', iid=entry_id, values=(ts_date, type.capitalize(), preview))
                
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to load entries: {e}")

    def on_entry_select(self, event):
        """Callback when an entry is selected from the Treeview."""
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        entry_id = selected_items[0] # The iid is the entry_id
        
        try:
            self.cursor.execute("SELECT type, content, tags, filepath, timestamp, description FROM entries WHERE id = ?", (entry_id,))
            entry = self.cursor.fetchone()
            if entry:
                self.display_entry(entry_id, entry)
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to fetch entry: {e}")

    def clear_display_frame(self):
        """Clears the scrollable content frame."""
        for widget in self.scrollable_content_frame.winfo_children():
            widget.destroy()
        self.photo_image = None
        # Reset scroll position
        self.display_canvas.yview_moveto(0)

    def show_welcome_message(self):
        """Displays a welcome message in the display area."""
        self.clear_display_frame()
        
        ttk.Label(
            self.scrollable_content_frame,
            text="Welcome to your Brain Dump!",
            style='Header.TLabel',
            background=FRAME_COLOR
        ).grid(row=0, column=0, pady=20, padx=20, sticky='w')
        
        info_text = "• Add notes, files, or paste images using the panel on the left.\n" \
                    "• Your entries will be saved locally on your computer.\n" \
                    "• Select an item from the list to view it here.\n" \
                    "• Use the search and tag filters to find your entries."
        
        ttk.Label(
            self.scrollable_content_frame,
            text=info_text,
            background=FRAME_COLOR,
            justify='left'
        ).grid(row=1, column=0, pady=10, padx=20, sticky='w')

    def display_entry(self, entry_id, entry_data):
        """Displays the selected entry (note or file) in the main display area."""
        self.clear_display_frame()
        
        type, content, tags, filepath, timestamp, description = entry_data
        
        # Frame for metadata
        meta_frame = ttk.Frame(self.scrollable_content_frame, style='Content.TFrame')
        meta_frame.grid(row=0, column=0, sticky='ew', pady=(5, 10), padx=5)
        
        ts_date = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').strftime('%c')
        
        meta_frame.columnconfigure(1, weight=1)
        ttk.Label(meta_frame, text="Type:", style='Bold.TLabel').grid(row=0, column=0, sticky='nw', padx=5, pady=2)
        ttk.Label(meta_frame, text=type.capitalize(), style='Meta.TLabel', foreground=TEXT_COLOR, wraplength=400).grid(row=0, column=1, sticky='w', padx=5, pady=2)
        
        ttk.Label(meta_frame, text="Saved:", style='Bold.TLabel').grid(row=1, column=0, sticky='nw', padx=5, pady=2)
        ttk.Label(meta_frame, text=ts_date, style='Meta.TLabel', wraplength=400).grid(row=1, column=1, sticky='w', padx=5, pady=2)
        
        if tags:
            ttk.Label(meta_frame, text="Tags:", style='Bold.TLabel').grid(row=2, column=0, sticky='nw', padx=5, pady=2)
            ttk.Label(meta_frame, text=tags, style='Meta.TLabel', wraplength=400).grid(row=2, column=1, sticky='w', padx=5, pady=2)
        
        ttk.Separator(self.scrollable_content_frame, orient='horizontal').grid(row=1, column=0, sticky='ew', pady=5, padx=5)
        
        content_frame = ttk.Frame(self.scrollable_content_frame, style='Content.TFrame')
        content_frame.grid(row=2, column=0, sticky='nsew')
        content_frame.columnconfigure(0, weight=1)

        if type == 'note':
            note_display = scrolledtext.ScrolledText(
                content_frame, wrap=tk.WORD, font=('Helvetica', 12),
                relief=tk.FLAT, bg=FRAME_COLOR, fg=TEXT_COLOR,
                bd=0, highlightthickness=0, height=25 # Give it a default height
            )
            note_display.insert("1.0", content)
            note_display.config(state=tk.DISABLED)
            note_display.grid(row=0, column=0, sticky='ew', padx=5)
            
        elif type == 'file':
            is_image = False
            if PIL_AVAILABLE and filepath and filepath.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                is_image = True
            
            row_counter = 0
            if is_image:
                try:
                    img = Image.open(filepath)
                    img_width, img_height = img.size
                    
                    # Simple resize logic: fit to a max width (calc from canvas)
                    max_width = self.display_canvas.winfo_width() - 20
                    if max_width < 100: max_width = 500 # Default if canvas not ready
                    
                    if img_width > max_width:
                        ratio = max_width / float(img_width)
                        new_height = int(img_height * ratio)
                        img = img.resize((int(max_width), new_height), Image.Resampling.LANCZOS)
                    
                    self.photo_image = ImageTk.PhotoImage(img)
                    preview_label = ttk.Label(content_frame, image=self.photo_image, background=FRAME_COLOR)
                    preview_label.grid(row=row_counter, column=0, pady=10); row_counter +=1
                except Exception as e:
                    ttk.Label(content_frame, text=f"Error loading image: {e}", background=FRAME_COLOR, foreground='#ff8a80').grid(row=row_counter, column=0, pady=5); row_counter +=1
                    ttk.Label(content_frame, text=content, font=('Helvetica', 14, 'bold'), background=FRAME_COLOR).grid(row=row_counter, column=0, pady=10); row_counter +=1
            else:
                ttk.Label(content_frame, text=content, font=('Helvetica', 14, 'bold'), background=FRAME_COLOR).grid(row=row_counter, column=0, pady=10); row_counter +=1
            
            ttk.Label(content_frame, text=f"Location: {filepath}", font=('Helvetica', 9, 'italic'), foreground=LIGHT_TEXT, background=FRAME_COLOR, wraplength=500).grid(row=row_counter, column=0, pady=5, sticky='w', padx=5); row_counter +=1
            
            if description:
                ttk.Separator(content_frame, orient='horizontal').grid(row=row_counter, column=0, sticky='ew', pady=(10, 5), padx=5); row_counter +=1
                ttk.Label(content_frame, text="Note:", style='Bold.TLabel', background=FRAME_COLOR).grid(row=row_counter, column=0, sticky='w', padx=5, pady=(5,0)); row_counter +=1
                
                desc_frame = ttk.Frame(content_frame, style='Content.TFrame')
                desc_frame.grid(row=row_counter, column=0, sticky='ew', pady=5, padx=5); row_counter +=1
                desc_frame.columnconfigure(0, weight=1)
                
                desc_text = scrolledtext.ScrolledText(
                    desc_frame, wrap=tk.WORD, font=('Helvetica', 11),
                    relief=tk.FLAT, bg=FRAME_COLOR, fg=TEXT_COLOR,
                    bd=0, highlightthickness=0, height=10 # Default height
                )
                desc_text.insert("1.0", description)
                desc_text.config(state=tk.DISABLED)
                desc_text.grid(row=0, column=0, sticky='ew', padx=5, pady=5)

            button_pack = ttk.Frame(content_frame, style='Content.TFrame')
            button_pack.grid(row=row_counter, column=0, pady=20); row_counter +=1

            open_button = ttk.Button(
                button_pack,
                text="Open File",
                command=lambda p=filepath: self.open_file_externally(p),
                style='TButton'
            )
            open_button.pack(side=tk.LEFT, padx=5)
            
            open_dir_button = ttk.Button(
                button_pack,
                text="Open File Location",
                command=lambda p=filepath: self.open_file_location(p),
                style='TButton'
            )
            open_dir_button.pack(side=tk.LEFT, padx=5)

        # Delete button at the bottom (inside scrollable frame)
        delete_button = ttk.Button(
            self.scrollable_content_frame,
            text="Delete This Entry",
            command=lambda id=entry_id: self.delete_entry(id)
        )
        delete_button.grid(row=3, column=0, pady=10, padx=5, sticky='se')

    def open_file_externally(self, filepath):
        """Opens the file using the system's default application."""
        try:
            if sys.platform == "win32":
                os.startfile(os.path.normpath(filepath))
            elif sys.platform == "darwin": # macOS
                subprocess.run(["open", filepath])
            else: # Linux and other UNIX-like
                subprocess.run(["xdg-open", filepath])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}\n\nPath: {filepath}")

    def open_file_location(self, filepath):
        """Opens the directory containing the file."""
        try:
            if sys.platform == "win32":
                subprocess.run(["explorer", "/select,", os.path.normpath(filepath)])
            elif sys.platform == "darwin": # macOS
                subprocess.run(["open", "-R", filepath])
            else: # Linux
                subprocess.run(["xdg-open", os.path.dirname(filepath)])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file location: {e}")

    def delete_entry(self, entry_id):
        """Deletes an entry from the database and its associated file (if any)."""
        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to permanently delete this entry?"):
            return
            
        try:
            self.cursor.execute("SELECT type, filepath FROM entries WHERE id = ?", (entry_id,))
            entry = self.cursor.fetchone()
            
            if entry:
                type, filepath = entry
                if type == 'file' and filepath and os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except OSError as e:
                        messagebox.showerror("File Error", f"Failed to delete file: {e}. The database entry will still be removed.")
            
            self.cursor.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
            self.conn.commit()
            
            # messagebox.showinfo("Deleted", "Entry has been deleted.") # Less intrusive
            self.load_entries()
            self.show_welcome_message()
            
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to delete entry: {e}")


def main():
    root = tk.Tk()
    app = BrainDumpApp(root)
    
    def on_closing():
        if app.conn:
            app.conn.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    if not PIL_AVAILABLE:
        print("---")
        print("WARNING: The 'Pillow' library is not installed.")
        print("Image pasting and preview features will be disabled.")
        print("To enable them, run: pip install Pillow")
        print("---")
    main()




