import os
import sys
import math
import time
import random
import tkinter as tk

# Windows-specific imports
try:
    import psutil
    import win32gui
    import win32process
    import win32con
    import win32api
    import win32console
except ImportError:
    print("Required packages (psutil, pywin32) are missing. Please run 'pip install psutil pywin32'")
    sys.exit(1)

coordinator_instance = None

# Constants
BUDDY_WIDTH = 100
BUDDY_HEIGHT = 100
GRAVITY = 0.8
BOUNCE_COOLDOWN = 1.0 # seconds between buddy collisions

def force_foreground_focus(hwnd):
    """Force focus to a window handle, bypassing Windows OS restrictions."""
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            
        # Try to attach thread input to allow focus stealing
        fore_hwnd = win32gui.GetForegroundWindow()
        fore_thread, _ = win32process.GetWindowThreadProcessId(fore_hwnd)
        curr_thread = win32api.GetCurrentThreadId()
        
        if fore_thread != curr_thread:
            try:
                win32process.AttachThreadInput(fore_thread, curr_thread, True)
                win32gui.SetForegroundWindow(hwnd)
                win32process.AttachThreadInput(fore_thread, curr_thread, False)
            except Exception:
                win32gui.SetForegroundWindow(hwnd)
        else:
            win32gui.SetForegroundWindow(hwnd)
            
        win32gui.SetActiveWindow(hwnd)
    except Exception as e:
        print(f"Error forcing window focus: {e}")

class CodeBug:
    def __init__(self, root, monitor_rect, buddy_floor_y):
        self.root = root
        self.width = 30
        self.height = 30
        left, top, right, bottom = monitor_rect
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        
        # Align bug's bottom to buddy's bottom/taskbar
        self.floor_y = buddy_floor_y + BUDDY_HEIGHT - self.height
        
        # Physics / Falling
        self.vy = 0.0
        
        # Select random edge: 0 = Left, 1 = Right, 2 = Top, 3 = Bottom
        edge = random.randint(0, 3)
        if edge == 0:  # Left Wall
            self.x = left
            self.y = self.floor_y
            self.vx = 2.0  # Move right
        elif edge == 1:  # Right Wall
            self.x = right - self.width
            self.y = self.floor_y
            self.vx = -2.0  # Move left
        elif edge == 2:  # Top Edge (Falls down)
            self.x = random.randint(left + 50, right - 50)
            self.y = top
            self.vx = random.choice([-1.5, 1.5])
        else:  # Bottom Edge (Floor)
            self.x = random.randint(left + 50, right - 50)
            self.y = self.floor_y
            self.vx = random.choice([-2.0, 2.0])
            
        self.direction = 1 if self.vx > 0 else -1
        self.tick = 0
        
        self.win = tk.Toplevel(self.root)
        self.win.overrideredirect(True)
        self.win.wm_attributes("-topmost", True)
        
        self.trans_color = "#FF00FF"
        self.win.wm_attributes("-transparentcolor", self.trans_color)
        
        self.canvas = tk.Canvas(self.win, width=self.width, height=self.height, bg=self.trans_color, highlightthickness=0)
        self.canvas.pack()
        
        self.update_geometry()
        
    def update_geometry(self):
        self.win.geometry(f"{self.width}x{self.height}+{int(self.x)}+{int(self.y)}")
        
    def update(self):
        # Apply gravity if above floor level
        if self.y < self.floor_y:
            self.vy += 0.8  # Gravity matching buddy
            self.y += self.vy
            self.x += self.vx
        else:
            self.vy = 0
            self.y = self.floor_y
            self.x += self.vx
            
        self.tick += 1
        
        # Crawl bounds
        if self.x <= self.left:
            self.x = self.left
            self.vx = -self.vx
            self.direction = 1
        elif self.x >= self.right - self.width:
            self.x = self.right - self.width
            self.vx = -self.vx
            self.direction = -1
            
        if self.y == self.floor_y and random.random() < 0.02:
            self.vx = -self.vx
            self.direction = 1 if self.vx > 0 else -1
            
        self.update_geometry()
        self.render()
        
    def render(self):
        self.canvas.delete("all")
        cx, cy = self.width / 2, self.height / 2 + 5
        
        # Leg wiggle
        leg = math.sin(self.tick * 0.7) * 2
        self.canvas.create_line(cx - 4, cy - 3, cx - 10, cy - 5 + leg, fill="#4A148C", width=2)
        self.canvas.create_line(cx - 4, cy, cx - 11, cy + leg, fill="#4A148C", width=2)
        self.canvas.create_line(cx - 4, cy + 3, cx - 10, cy + 5 - leg, fill="#4A148C", width=2)
        
        self.canvas.create_line(cx + 4, cy - 3, cx + 10, cy - 5 - leg, fill="#4A148C", width=2)
        self.canvas.create_line(cx + 4, cy, cx + 11, cy - leg, fill="#4A148C", width=2)
        self.canvas.create_line(cx + 4, cy + 3, cx + 10, cy + 5 + leg, fill="#4A148C", width=2)
        
        # Beetle body
        self.canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill="#7B1FA2", outline="black")
        self.canvas.create_oval(cx + self.direction * 5 - 2, cy - 2, cx + self.direction * 5 + 2, cy + 2, fill="black")

class BaseBuddyWindow:
    def __init__(self, root, mascot_type="generic"):
        self.root = root
        self.mascot_type = mascot_type
        
        # Physics state
        self.width = BUDDY_WIDTH
        self.height = BUDDY_HEIGHT
        
        # Screen dimensions
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        
        # Taskbar/Floor level using primary monitor work area rect
        left, top, right, bottom = (0, 0, self.screen_width, self.screen_height)
        try:
            import win32api
            monitors = win32api.EnumDisplayMonitors()
            if monitors:
                try:
                    info = win32api.GetMonitorInfo(monitors[0][0])
                    left, top, right, bottom = info['Work']
                except Exception:
                    left, top, right, bottom = monitors[0][2]
        except Exception:
            pass
            
        self.floor_y = bottom - self.height
        self.x = random.randint(left + 100, right - 200)
        self.y = self.floor_y
        self.vx = random.choice([-2.0, -1.5, 1.5, 2.0])
        self.vy = 0.0
        
        # Behaviors: 'idle', 'walking', 'climbing', 'falling', 'alert', 'sleeping'
        self.state = "idle"
        self.direction = 1 if self.vx > 0 else -1 # 1 = Right, -1 = Left
        self.climb_wall = None # 'left' or 'right'
        
        # Interactive flags
        self.is_dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.last_drag_time = 0
        self.drag_path = [] # list of (time, x, y) to calculate throw velocity
        self.alert_active = False
        self.mute_alerts = False
        self.paused = False
        
        # Activity & Chasing States
        self.activity_state = None # 'writing' or 'researching'
        self.happy_timer = 0
        
        # Animation
        self.tick = random.randint(0, 100)
        self.squash_tick = 0 # squash frames remaining
        self.squash_type = None # 'land' or 'launch'
        
        # Snoring particles for sleeping state
        self.snores = [] # list of dicts: {'x': x, 'y': y, 'char': 'z', 'size': s, 'age': a}
        self.dust_particles = []
        self.jetpack_smoke = []
        self.confetti = []
        self.music_notes = []
        self.track_name = ""
        
        # Setup Toplevel Window
        self.win = tk.Toplevel(self.root)
        self.win.overrideredirect(True)
        self.win.wm_attributes("-topmost", True)
        
        # Chroma key transparency
        self.trans_color = "#FF00FF" # Magenta
        self.win.wm_attributes("-transparentcolor", self.trans_color)
        
        # Canvas
        self.canvas = tk.Canvas(self.win, width=self.width, height=self.height, bg=self.trans_color, highlightthickness=0)
        self.canvas.pack()
        
        self.click_job = None
        self.double_click_job = None
        
        # Event bindings
        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)
        self.canvas.bind("<Triple-Button-1>", self.on_triple_click)
        self.canvas.bind("<Button-3>", self.show_context_menu)
        
        # Context Menu
        self.menu = tk.Menu(self.win, tearoff=0)
        self.menu.add_command(label="Mark Alert as Read", command=self.dismiss_alert)
        self.menu.add_command(label="Mute Alerts", command=self.toggle_mute)
        self.menu.add_command(label="Hold Buddy", command=self.toggle_pause)
        self.menu.add_command(label="Spawn Code Bug", command=self.spawn_bug_click)
        self.menu.add_separator()
        self.menu.add_command(label="Exit Pal", command=self.root.destroy)
        
        # Sync geometry
        self.update_geometry()
        
    def update_geometry(self):
        self.win.geometry(f"{self.width}x{self.height}+{int(self.x)}+{int(self.y)}")
        
    def on_left_click(self, event):
        self.is_dragging = True
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.press_x = event.x
        self.press_y = event.y
        self.press_time = time.time()
        self.last_drag_time = time.time()
        self.drag_path = [(self.last_drag_time, self.x, self.y)]
        self.vx = 0
        self.vy = 0
        self.state = "idle"
        self.giggle_triggered = False
        
    def on_drag(self, event):
        if self.is_dragging:
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y
            self.x += dx
            self.y += dy
            
            # Constrain to overall virtual screen boundaries during drag
            # (Allows dragging between multiple monitors smoothly)
            try:
                import win32api
                import win32con
                virtual_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
                virtual_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
                virtual_width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
                virtual_height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
                
                self.x = max(virtual_left, min(virtual_left + virtual_width - self.width, self.x))
                self.y = max(virtual_top, min(virtual_top + virtual_height - self.height, self.y))
            except Exception:
                self.x = max(0, min(self.screen_width - self.width, self.x))
                self.y = max(0, min(self.screen_height - self.height, self.y))
                
            self.update_geometry()
            
            # Record track for throwing physics (moved back to on_drag)
            now = time.time()
            self.drag_path.append((now, self.x, self.y))
            if len(self.drag_path) > 10:
                self.drag_path.pop(0)
                
            # Trigger giggle next/random song ONLY once when the drag starts
            if hasattr(self, 'press_x') and hasattr(self, 'giggle_triggered') and not self.giggle_triggered:
                drag_dist = math.hypot(event.x - self.press_x, event.y - self.press_y)
                if drag_dist >= 6:
                    self.giggle_triggered = True
                    if self.mascot_type == "spotify":
                        import win32api
                        import win32con
                        # VK_MEDIA_NEXT_TRACK = 0xB0
                        win32api.keybd_event(0xB0, 0, 0, 0)
                        win32api.keybd_event(0xB0, 0, win32con.KEYEVENTF_KEYUP, 0)
                        print("Spotify Buddy: Giggle Grabbed! Sent Media Next Track (Random song)")
            
    def get_current_monitor_rect(self):
        """Detect which monitor the buddy window is currently on and return its work area."""
        try:
            import win32api
            monitors = win32api.EnumDisplayMonitors()
            cx = self.x + self.width / 2
            cy = self.y + self.height / 2
            
            # Check if buddy is inside any monitor
            for handle, device, rect in monitors:
                left, top, right, bottom = rect
                if left <= cx <= right and top <= cy <= bottom:
                    try:
                        info = win32api.GetMonitorInfo(handle)
                        return info['Work']
                    except Exception:
                        return rect
                    
            # Fallback: Find closest monitor
            closest_rect = None
            min_dist = 99999999
            for handle, device, rect in monitors:
                left, top, right, bottom = rect
                mid_x = (left + right) / 2
                mid_y = (top + bottom) / 2
                dist = (cx - mid_x)**2 + (cy - mid_y)**2
                if dist < min_dist:
                    min_dist = dist
                    try:
                        info = win32api.GetMonitorInfo(handle)
                        closest_rect = info['Work']
                    except Exception:
                        closest_rect = rect
            if closest_rect:
                return closest_rect
        except Exception:
            pass
        return (0, 0, self.screen_width, self.screen_height)

    def get_monitor_rect_from_window(self, hwnd):
        """Query which monitor a specific window handle resides on and return its work area."""
        try:
            import win32api
            import win32con
            monitor_handle = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
            monitor_info = win32api.GetMonitorInfo(monitor_handle)
            return monitor_info['Work'] # (left, top, right, bottom)
        except Exception:
            return None
                
    def on_release(self, event):
        self.is_dragging = False
        
        # Calculate throw velocity
        if len(self.drag_path) >= 2:
            t1, x1, y1 = self.drag_path[0]
            t2, x2, y2 = self.drag_path[-1]
            dt = t2 - t1
            if dt > 0.05:
                self.vx = (x2 - x1) / (dt * 60) # scaled velocity
                self.vy = (y2 - y1) / (dt * 60)
                
                # Cap velocity
                self.vx = max(-15, min(15, self.vx))
                self.vy = max(-20, min(10, self.vy))
                
        self.state = "falling"
        
        # Check for single click
        if hasattr(self, 'press_time'):
            drag_dist = math.hypot(event.x - self.press_x, event.y - self.press_y)
            elapsed = time.time() - self.press_time
            if drag_dist < 5 and elapsed < 0.25:
                # Cancel previous click job if active
                if hasattr(self, 'click_job') and self.click_job:
                    try:
                        self.root.after_cancel(self.click_job)
                    except Exception:
                        pass
                    self.click_job = None
                self.click_job = self.root.after(220, self.perform_single_click)

    def on_double_click(self, event):
        if hasattr(self, 'click_job') and self.click_job:
            try:
                self.root.after_cancel(self.click_job)
            except Exception:
                pass
            self.click_job = None
            
        if hasattr(self, 'double_click_job') and self.double_click_job:
            try:
                self.root.after_cancel(self.double_click_job)
            except Exception:
                pass
            self.double_click_job = None
            
        self.double_click_job = self.root.after(220, self.perform_double_click)

    def on_triple_click(self, event):
        if hasattr(self, 'click_job') and self.click_job:
            try:
                self.root.after_cancel(self.click_job)
            except Exception:
                pass
            self.click_job = None
            
        if hasattr(self, 'double_click_job') and self.double_click_job:
            try:
                self.root.after_cancel(self.double_click_job)
            except Exception:
                pass
            self.double_click_job = None
            
        self.perform_triple_click()

    def perform_single_click(self):
        self.click_job = None
        pal_def = PAL_REGISTRY.get(self.keyword)
        if pal_def and pal_def.on_single_click_fn:
            pal_def.on_single_click_fn(self)

    def perform_double_click(self):
        self.double_click_job = None
        pal_def = PAL_REGISTRY.get(self.keyword)
        if pal_def and pal_def.on_double_click_fn:
            pal_def.on_double_click_fn(self)
        else:
            if hasattr(self, 'focus_agent_window'):
                self.focus_agent_window()

    def perform_triple_click(self):
        pal_def = PAL_REGISTRY.get(self.keyword)
        if pal_def and pal_def.on_triple_click_fn:
            pal_def.on_triple_click_fn(self)
        
    def show_context_menu(self, event):
        # Dynamically enable/disable "Mark Alert as Read" if there is an active alert
        has_alert = self.alert_active or (hasattr(self, 'success_timer') and self.success_timer > 0)
        state = "normal" if has_alert else "disabled"
        try:
            self.menu.entryconfig("Mark Alert as Read", state=state)
        except Exception:
            pass
        self.menu.post(event.x_root, event.y_root)
        
    def dismiss_alert(self):
        self.alert_active = False
        if hasattr(self, 'success_timer'):
            self.success_timer = 0
            
    def toggle_mute(self):
        self.mute_alerts = not self.mute_alerts
        self.menu.entryconfig(0, label="Unmute Alerts" if self.mute_alerts else "Mute Alerts")
        
    def toggle_pause(self):
        self.paused = not self.paused
        self.menu.entryconfig(1, label="Release Buddy" if self.paused else "Hold Buddy")
        if self.paused:
            self.vx = 0
            self.vy = 0
            self.state = "idle"
            
    def spawn_bug_click(self):
        global coordinator_instance
        if coordinator_instance:
            coordinator_instance.spawn_bug()
            
    def trigger_squash(self, stype, frames=6):
        self.squash_tick = frames
        self.squash_type = stype
        if stype == "land":
            self.spawn_dust_cloud(self.width / 2, self.height / 2 + 15)

    def spawn_dust_cloud(self, cx, cy):
        colors = ["#90A4AE", "#B0BEC5", "#CFD8DC", "#ECEFF1"]
        for _ in range(8):
            vx = random.uniform(-2.5, 2.5)
            vy = random.uniform(-1.2, -0.2)
            self.dust_particles.append({
                'x': cx + random.uniform(-8, 8),
                'y': cy + 10, # feet level
                'vx': vx,
                'vy': vy,
                'size': random.uniform(3, 7),
                'color': random.choice(colors),
                'age': 0,
                'max_age': random.randint(12, 20)
            })

    def spawn_jetpack_trail(self, cx, cy, sx, sy):
        colors = ["#FF5722", "#FF9800", "#FFC107", "#CFD8DC", "#ECEFF1"]
        for offset in [-10 * sx, 10 * sx]:
            self.jetpack_smoke.append({
                'x': cx + offset + random.uniform(-2, 2),
                'y': cy + 16 * sy,
                'vx': random.uniform(-0.8, 0.8) - (0.3 * self.vx if hasattr(self, 'vx') else 0),
                'vy': random.uniform(1.5, 3.5),
                'size': random.uniform(3, 6),
                'color': random.choice(colors),
                'age': 0,
                'max_age': random.randint(10, 18)
            })

    def spawn_confetti(self):
        colors = ["#E91E63", "#9C27B0", "#2196F3", "#4CAF50", "#FFEB3B", "#FF9800", "#00BCD4"]
        self.confetti.append({
            'x': random.uniform(10, self.width - 10),
            'y': 0,
            'vx': random.uniform(-1.0, 1.0),
            'vy': random.uniform(1.2, 2.8),
            'size': random.uniform(2, 5),
            'color': random.choice(colors),
            'age': 0,
            'max_age': random.randint(35, 55)
        })

    def spawn_music_note(self, cx, cy):
        notes_chars = ["♪", "♫", "♩", "♬"]
        colors = ["#1DB954", "#1ED760", "#57B560", "#A5D6A7", "#E8F5E9"]
        self.music_notes.append({
            'x': cx + random.uniform(-15, 15),
            'y': cy - 10,
            'vx': random.uniform(-1.0, 1.0),
            'vy': random.uniform(-2.0, -0.8),
            'size': random.randint(10, 16),
            'char': random.choice(notes_chars),
            'color': random.choice(colors),
            'age': 0,
            'max_age': random.randint(25, 40)
        })

    def spawn_giggle_particle(self, cx, cy):
        giggles = ["hehe", "haha", "giggle", "hihi", "ツ"]
        colors = ["#1DB954", "#1ED760", "#A5D6A7", "#ffffff"]
        self.music_notes.append({
            'x': cx + random.uniform(-25, 25),
            'y': cy + random.uniform(-20, 10),
            'vx': random.uniform(-1.5, 1.5),
            'vy': random.uniform(-2.5, -1.0),
            'size': random.randint(8, 12),
            'char': random.choice(giggles),
            'color': random.choice(colors),
            'age': 0,
            'max_age': random.randint(20, 30)
        })

    def draw_and_update_custom_particles(self):
        # 1. Dust Particles
        alive_dust = []
        for p in self.dust_particles:
            p['age'] += 1
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vy'] += 0.05 # minor gravity
            
            alpha = max(0, 100 - int((p['age'] / p['max_age']) * 100))
            if alpha > 0 and p['age'] < p['max_age']:
                r = p['size'] * (alpha / 100.0)
                if r > 0.5:
                    self.canvas.create_oval(
                        p['x'] - r, p['y'] - r, p['x'] + r, p['y'] + r,
                        fill=p['color'], outline=""
                    )
                    alive_dust.append(p)
        self.dust_particles = alive_dust

        # 2. Confetti
        alive_confetti = []
        for p in self.confetti:
            p['age'] += 1
            p['x'] += p['vx'] + math.sin(p['age'] * 0.15) * 1.2
            p['y'] += p['vy']
            
            alpha = max(0, 100 - int((p['age'] / p['max_age']) * 100))
            if alpha > 0 and p['age'] < p['max_age'] and p['y'] < self.height:
                r = p['size']
                self.canvas.create_rectangle(
                    p['x'] - r, p['y'] - r, p['x'] + r, p['y'] + r,
                    fill=p['color'], outline=""
                )
                alive_confetti.append(p)
        self.confetti = alive_confetti

        # 3. Jetpack Smoke
        alive_smoke = []
        for p in self.jetpack_smoke:
            p['age'] += 1
            p['x'] += p['vx'] + math.sin(p['age'] * 0.2) * 0.5
            p['y'] += p['vy']
            
            alpha = max(0, 100 - int((p['age'] / p['max_age']) * 100))
            if alpha > 0 and p['age'] < p['max_age']:
                r = p['size'] * (alpha / 100.0)
                if r > 0.5:
                    self.canvas.create_oval(
                        p['x'] - r, p['y'] - r, p['x'] + r, p['y'] + r,
                        fill=p['color'], outline=""
                    )
                    alive_smoke.append(p)
        self.jetpack_smoke = alive_smoke

        # 4. Music Notes
        if hasattr(self, 'music_notes') and self.music_notes:
            alive_notes = []
            for n in self.music_notes:
                n['age'] += 1
                n['x'] += n['vx'] + math.sin(n['age'] * 0.1) * 0.8
                n['y'] += n['vy']
                
                alpha = max(0, 100 - int((n['age'] / n['max_age']) * 100))
                if alpha > 0 and n['age'] < n['max_age']:
                    size = int(n['size'] * (alpha / 100.0))
                    if size >= 6:
                        self.canvas.create_text(
                            n['x'], n['y'],
                            text=n['char'],
                            fill=n['color'],
                            font=("Arial", size, "bold")
                        )
                        alive_notes.append(n)
            self.music_notes = alive_notes
        
    def draw_success_bubble(self, t):
        """Draw a floating green checkmark bubble above the head."""
        cx = self.width / 2
        cy = 20
        cy += math.sin(t * 0.25) * 4
        
        # Green circle
        self.canvas.create_oval(cx - 10, cy - 10, cx + 10, cy + 10, fill="#00E676", outline="white", width=2)
        # Tail
        self.canvas.create_polygon(cx - 3, cy + 9, cx + 3, cy + 9, cx, cy + 14, fill="#00E676", outline="")
        # White checkmark ✔
        self.canvas.create_line(cx - 5, cy, cx - 1, cy + 4, fill="white", width=2)
        self.canvas.create_line(cx - 1, cy + 4, cx + 5, cy - 4, fill="white", width=2)
        
    def draw_happy_sparkles(self, cx, cy):
        """Draw sparkling yellow stars for celebration."""
        for angle in [0, 90, 180, 270]:
            rad = math.radians(angle + self.tick * 6)
            sx = cx + math.cos(rad) * 16
            sy = cy - 25 + math.sin(rad) * 16
            self.canvas.create_text(sx, sy, text="✦", fill="#FFD54F", font=("Arial", 10))
            
    def draw_busy_accessories(self, cx, cy):
        """Draw typing keyboard or researching magnifying glass in busy state."""
        t = self.tick
        if self.activity_state == "writing":
            # Slanted keyboard
            self.canvas.create_polygon(cx - 20 * self.direction, cy + 12, 
                                        cx + 20 * self.direction, cy + 12, 
                                        cx + 15 * self.direction, cy + 22, 
                                        cx - 15 * self.direction, cy + 22, 
                                        fill="#757575", outline="#424242")
            self.canvas.create_line(cx - 10, cy + 15, cx + 10, cy + 15, fill="#E0E0E0")
            self.canvas.create_line(cx - 12, cy + 19, cx + 12, cy + 19, fill="#E0E0E0")
            # Typing hands
            j_l = math.sin(t * 1.5) * 3
            j_r = math.cos(t * 1.5) * 3
            self.canvas.create_oval(cx - 12, cy + 6 + j_l, cx - 7, cy + 11 + j_l, fill="#FFE082", outline="")
            self.canvas.create_oval(cx + 7, cy + 6 + j_r, cx + 12, cy + 11 + j_r, fill="#FFE082", outline="")
        elif self.activity_state == "researching":
            # Bobbing magnifying glass
            bob = math.sin(t * 0.4) * 3
            gx = cx + self.direction * 18
            gy = cy - 2 + bob
            self.canvas.create_line(gx, gy, gx + self.direction * 8, gy + 8, fill="#8D6E63", width=3)
            self.canvas.create_oval(gx - 6, gy - 6, gx + 6, gy + 6, fill="#E0F7FA", outline="#37474F", width=2)
            self.canvas.create_line(gx - 3, gy - 3, gx + 1, gy + 1, fill="white")
        
    def update_physics(self):
        if self.paused or self.is_dragging:
            return
            
        # Resolve active monitor boundaries dynamically
        left, top, right, bottom = self.get_current_monitor_rect()
        self.floor_y = bottom - self.height
        
        # Happy squashed celebration state
        if self.state == "happy":
            self.vx = 0
            self.vy = 0
            self.happy_timer -= 1
            if self.happy_timer <= 0:
                self.state = "idle"
            self.update_geometry()
            return
            
        # 1. Climbing State
        if self.state == "climbing":
            self.vy = -1.5 # climb up slowly
            self.y += self.vy
            self.vx = 0
            
            # Snapping to wall x of active monitor
            if self.climb_wall == "left":
                self.x = left
                self.direction = 1 # face screen inside
            else:
                self.x = right - self.width
                self.direction = -1
                
            # Randomly jump off wall
            if random.random() < 0.015:
                self.state = "falling"
                self.climb_wall = None
                self.vx = 5.0 if self.direction == 1 else -5.0
                self.vy = -8.0 # push off jump
                self.trigger_squash("launch")
                
            # Reach top of screen -> slide down
            if self.y <= top + 40:
                self.state = "falling"
                self.climb_wall = None
                self.vx = 3.0 if self.direction == 1 else -3.0
                
            self.update_geometry()
            return
            
        # 2. Gravity / Falling State
        if self.y < self.floor_y:
            self.vy += GRAVITY
            if self.state != "falling":
                self.state = "falling"
        else:
            self.vy = 0
            # If we were falling and just hit the floor -> land
            if self.state == "falling":
                self.state = "idle"
                self.vx = random.choice([-1.5, 1.5])
                self.trigger_squash("land", 8)
                
        # Bug Chasing Logic Integration
        global coordinator_instance
        reacts_to_bugs = True
        pal_def = None
        for pd in PAL_REGISTRY.values():
            if pd.mascot_type == self.mascot_type:
                pal_def = pd
                break
        if pal_def:
            reacts_to_bugs = pal_def.reacts_to_bugs
            
        if coordinator_instance and coordinator_instance.bugs and self.state in ["idle", "walking", "chasing"] and reacts_to_bugs:
            closest_bug = None
            min_dist = 999999
            for bug in coordinator_instance.bugs:
                dist = abs(self.x - bug.x)
                if dist < min_dist:
                    min_dist = dist
                    closest_bug = bug
                    
            if closest_bug:
                self.state = "chasing"
                self.direction = 1 if closest_bug.x > self.x else -1
                self.vx = self.direction * 3.5
                
                # Hop & squash if directly on it
                if abs(self.x - closest_bug.x) < 20 and abs((self.y + self.height) - (closest_bug.y + closest_bug.height)) < 25:
                    self.vx = 0
                    self.vy = -6.0
                    self.state = "falling"
                    self.trigger_squash("launch", 5)
                    coordinator_instance.squash_bug(closest_bug)
                    
                    # Happy squish state
                    self.state = "happy"
                    self.happy_timer = 60 # Celebrate 2 seconds
                    self.trigger_squash("land", 12)
                    self.update_geometry()
                    return
        elif self.state == "chasing":
            # Bug was squashed by another buddy or disappeared, return to idle
            self.state = "idle"
            self.vx = random.choice([-1.5, 1.5])
                    
        # Apply velocity
        self.x += self.vx
        self.y += self.vy
        
        # Screen floor collision
        if self.y >= self.floor_y:
            self.y = self.floor_y
            
        # Side wall collision of active monitor (transition to climbing or bounce)
        if self.x <= left:
            self.x = left
            if self.state == "falling" or random.random() < 0.4:
                self.state = "climbing"
                self.climb_wall = "left"
            else:
                self.vx = -self.vx
                self.direction = 1
        elif self.x >= right - self.width:
            self.x = right - self.width
            if self.state == "falling" or random.random() < 0.4:
                self.state = "climbing"
                self.climb_wall = "right"
            else:
                self.vx = -self.vx
                self.direction = -1
                
        # 3. Roaming Floor Behavior (Idle/Walking)
        if self.state in ["idle", "walking"]:
            if self.state == "idle":
                self.vx = 0
                if random.random() < 0.02: # Waking up/walking
                    self.state = "walking"
                    self.direction = random.choice([-1, 1])
                    self.vx = self.direction * random.choice([1.5, 2.0])
                elif random.random() < 0.005: # Random small jump
                    self.vy = -7.0
                    self.vx = self.direction * 3.0
                    self.state = "falling"
                    self.trigger_squash("launch")
            elif self.state == "walking":
                self.vx = self.direction * 2.0
                if random.random() < 0.015: # Go idle
                    self.state = "idle"
                    self.vx = 0
                elif random.random() < 0.01: # Change direction
                    self.direction = -self.direction
                    self.vx = self.direction * 2.0
                elif random.random() < 0.008: # Jump forward
                    self.vy = -8.0
                    self.vx = self.direction * 3.5
                    self.state = "falling"
                    self.trigger_squash("launch")
                    
        self.update_geometry()
        
    def draw_alert_bubble(self, t):
        """Draw floating alert speech bubble above the head."""
        if self.mute_alerts:
            return
            
        cx = self.width / 2
        cy = 20
        # Float bobbing
        cy += math.sin(t * 0.2) * 4
        
        # Red warning balloon
        self.canvas.create_oval(cx - 10, cy - 10, cx + 10, cy + 10, fill="#FF1744", outline="white", width=2)
        # Tail
        self.canvas.create_polygon(cx - 3, cy + 9, cx + 3, cy + 9, cx, cy + 14, fill="#FF1744", outline="")
        # ! glyph
        self.canvas.create_rectangle(cx - 1.5, cy - 5, cx + 1.5, cy + 1, fill="white", outline="")
        self.canvas.create_oval(cx - 1.5, cy + 3, cx + 1.5, cy + 7, fill="white", outline="")
        
    def draw_snores(self, cx, cy):
        """Manage and draw snoring 'zZZ' floating bubbles."""
        # Spawn snore particle
        if self.tick % 45 == 0:
            self.snores.append({
                'x': cx + random.randint(10, 20),
                'y': cy - 10,
                'char': random.choice(['z', 'Z']),
                'size': random.choice([8, 10, 12]),
                'age': 0
            })
            
        # Draw and update particles
        alive_snores = []
        for p in self.snores:
            p['age'] += 1
            p['x'] += math.sin(p['age'] * 0.15) * 0.8 # drift sway
            p['y'] -= 0.8 # drift up
            
            # Fade out by color conversion (grey shades)
            alpha = max(0, 100 - (p['age'] * 2))
            if alpha > 0:
                color = f"#{alpha:02x}{alpha:02x}{alpha:02x}"
                self.canvas.create_text(p['x'], p['y'], text=p['char'], fill=color, font=("Courier New", p['size'], "bold"))
                alive_snores.append(p)
        self.snores = alive_snores
        
    def render(self):
        """Render vector shapes of the buddy."""
        self.canvas.delete("all")
        
        # Squash and stretch scale factors
        scale_x = 1.0
        scale_y = 1.0
        
        if self.squash_tick > 0:
            self.squash_tick -= 1
            if self.squash_type == "land":
                scale_x = 1.25
                scale_y = 0.75
            elif self.squash_type == "launch":
                scale_x = 0.8
                scale_y = 1.2
        elif self.state == "falling":
            scale_x = 0.9
            scale_y = 1.1
            
        cx, cy = self.width / 2, self.height / 2 + 15
        
        # Adjust vertical position for squashed base
        if scale_y < 1.0:
            cy += (1.0 - scale_y) * 20
            
        # Draw specific skin
        pal_def = None
        for pd in PAL_REGISTRY.values():
            if pd.mascot_type == self.mascot_type:
                pal_def = pd
                break
                
        if pal_def and pal_def.draw_skin_fn:
            pal_def.draw_skin_fn(self, cx, cy, scale_x, scale_y)
        else:
            self.draw_generic_skin(cx, cy, scale_x, scale_y)
            
        # Draw coding/research accessories (only if not chasing or celebrating)
        if self.activity_state and self.state not in ["chasing", "happy"]:
            self.draw_busy_accessories(cx, cy)
            
        # Render overlays
        if self.state == "happy":
            self.draw_happy_sparkles(cx, cy)
            
        if hasattr(self, 'success_timer') and self.success_timer > 0:
            self.draw_success_bubble(self.tick)
            # Spawn confetti!
            if self.tick % 3 == 0:
                self.spawn_confetti()
        elif self.alert_active:
            self.draw_alert_bubble(self.tick)
            
        # Draw premium custom particles
        self.draw_and_update_custom_particles()
        
        self.tick += 1
        
    def draw_antigravity_skin(self, cx, cy, sx, sy):
        t = self.tick
        
        # 1. Jetpack flames (drawn behind body)
        if self.state in ["falling", "climbing"] or (self.state == "idle" and t % 20 < 15):
            flame_len = (math.sin(t * 0.4) + 1.2) * 8 * sy
            self.canvas.create_oval(cx - 15 * sx, cy + 16 * sy, cx - 5 * sx, cy + (16 + flame_len) * sy, fill="#FF5722", outline="")
            self.canvas.create_oval(cx + 5 * sx, cy + 16 * sy, cx + 15 * sx, cy + (16 + flame_len) * sy, fill="#FF5722", outline="")
            self.canvas.create_oval(cx - 12 * sx, cy + 16 * sy, cx - 8 * sx, cy + (16 + flame_len * 0.6) * sy, fill="#FFC107", outline="")
            self.canvas.create_oval(cx + 8 * sx, cy + 16 * sy, cx + 12 * sx, cy + (16 + flame_len * 0.6) * sy, fill="#FFC107", outline="")
            
            # Spawn premium jetpack trail particles
            if t % 2 == 0:
                self.spawn_jetpack_trail(cx, cy, sx, sy)
            
        # 2. Main suit body (Deep blue sphere)
        self.canvas.create_oval(cx - 20 * sx, cy - 20 * sy, cx + 20 * sx, cy + 20 * sy, fill="#1976D2", outline="#0D47A1", width=2)
        
        # 3. Visor/Helmet
        self.canvas.create_oval(cx - 15 * sx, cy - 10 * sy, cx + 15 * sx, cy + 8 * sy, fill="#E3F2FD", outline="#90CAF9", width=2)
        
        # 4. Eyes (Blink)
        blink = (t % 80) > 76
        if not blink:
            # Shift eyes slightly based on walking direction
            look_x = self.direction * 3 * sx
            self.canvas.create_oval(cx - 7 * sx + look_x, cy - 3 * sy, cx - 3 * sx + look_x, cy + 1 * sy, fill="#1976D2", outline="")
            self.canvas.create_oval(cx + 3 * sx + look_x, cy - 3 * sy, cx + 7 * sx + look_x, cy + 1 * sy, fill="#1976D2", outline="")
            # Shiny glints
            self.canvas.create_oval(cx - 6 * sx + look_x, cy - 3 * sy, cx - 4 * sx + look_x, cy - 1 * sy, fill="white", outline="")
            self.canvas.create_oval(cx + 4 * sx + look_x, cy - 3 * sy, cx + 6 * sx + look_x, cy - 1 * sy, fill="white", outline="")

    def draw_claude_skin(self, cx, cy, sx, sy):
        t = self.tick
        
        # Walk foot bounce
        leg_sway = 0.0
        if self.state == "walking":
            leg_sway = math.sin(t * 0.25) * 8 * sy
            cy -= abs(math.sin(t * 0.25)) * 3 * sy
            
        # 1. Antenna
        self.canvas.create_line(cx, cy - 20 * sy, cx, cy - 28 * sy, fill="#E64A19", width=2)
        ant_glow = (t % 15) > 8
        self.canvas.create_oval(cx - 3 * sx, cy - 31 * sy, cx + 3 * sx, cy - 27 * sy, fill="#FF8A65" if ant_glow else "#D84315", outline="")
        
        # 2. Main Terminal Body (Coral Orange rounded box)
        self.canvas.create_rectangle(cx - 20 * sx, cy - 20 * sy, cx + 20 * sx, cy + 15 * sy, fill="#FF7043", outline="#E64A19", width=2)
        
        # 3. Inner Screen
        self.canvas.create_rectangle(cx - 15 * sx, cy - 15 * sy, cx + 15 * sx, cy + 10 * sy, fill="#212121", outline="")
        
        # 4. Eyes (Green shell code cursor)
        blink = (t % 70) > 66
        if not blink:
            look_x = self.direction * 2
            self.canvas.create_text(cx - 7 * sx + look_x, cy - 2 * sy, text=">", fill="#00E676", font=("Courier New", int(8 * sy), "bold"))
            self.canvas.create_text(cx + 7 * sx + look_x, cy - 2 * sy, text="_", fill="#00E676" if t % 10 < 5 else "#212121", font=("Courier New", int(8 * sy), "bold"))
            
        # 5. Legs
        if self.state != "climbing":
            self.canvas.create_rectangle(cx - 12 * sx, cy + 15 * sy, cx - 5 * sx, cy + (22 + leg_sway) * sy, fill="#D84315", outline="")
            self.canvas.create_rectangle(cx + 5 * sx, cy + 15 * sy, cx + 12 * sx, cy + (22 - leg_sway) * sy, fill="#D84315", outline="")
        else:
            # Climbing legs (drawn horizontal grasping wall)
            self.canvas.create_rectangle(cx - 20 * sx, cy - 10 * sy, cx - 25 * sx, cy - 5 * sy, fill="#D84315", outline="")
            self.canvas.create_rectangle(cx - 20 * sx, cy + 5 * sy, cx - 25 * sx, cy + 10 * sy, fill="#D84315", outline="")

    def draw_generic_skin(self, cx, cy, sx, sy):
        t = self.tick
        
        # Snoring particles in sleeping state
        if self.state == "sleeping":
            self.draw_snores(cx, cy)
            
        # Walk foot bounce
        leg_sway = 0.0
        if self.state == "walking":
            leg_sway = math.sin(t * 0.25) * 8 * sy
            cy -= abs(math.sin(t * 0.25)) * 3 * sy
            
        # 1. Main Head (Teal Terminal Box)
        # In sleeping state, lower the body and lay it horizontal
        if self.state == "sleeping":
            # Sleepy flat monitor
            self.canvas.create_rectangle(cx - 20 * sx, cy - 5 * sy, cx + 20 * sx, cy + 18 * sy, fill="#00897B", outline="#004D40", width=2)
            self.canvas.create_rectangle(cx - 15 * sx, cy - 1 * sy, cx + 15 * sx, cy + 14 * sy, fill="#004D40", outline="")
            # Sleepy closed eyes (crosses or lines)
            self.canvas.create_text(cx - 6 * sx, cy + 6 * sy, text="u", fill="#4DB6AC", font=("Courier New", int(8 * sy), "bold"))
            self.canvas.create_text(cx + 6 * sx, cy + 6 * sy, text="u", fill="#4DB6AC", font=("Courier New", int(8 * sy), "bold"))
            return
            
        self.canvas.create_rectangle(cx - 18 * sx, cy - 18 * sy, cx + 18 * sx, cy + 14 * sy, fill="#00897B", outline="#004D40", width=2)
        
        # 2. Inner screen
        self.canvas.create_rectangle(cx - 13 * sx, cy - 13 * sy, cx + 13 * sx, cy + 9 * sy, fill="#121212", outline="")
        
        # 3. Blinking Terminal Eyes
        blink = (t % 100) > 96
        if not blink:
            look_x = self.direction * 2
            # Bright cyan/green matrix eyes
            self.canvas.create_oval(cx - 7 * sx + look_x, cy - 4 * sy, cx - 3 * sx + look_x, cy, fill="#00F5FF", outline="")
            self.canvas.create_oval(cx + 3 * sx + look_x, cy - 4 * sy, cx + 7 * sx + look_x, cy, fill="#00F5FF", outline="")
            
        # 4. Legs
        if self.state != "climbing":
            self.canvas.create_rectangle(cx - 10 * sx, cy + 14 * sy, cx - 4 * sx, cy + (21 + leg_sway) * sy, fill="#004D40", outline="")
            self.canvas.create_rectangle(cx + 4 * sx, cy + 14 * sy, cx + 10 * sx, cy + (21 - leg_sway) * sy, fill="#004D40", outline="")

    def draw_now_playing_bubble(self, cx, cy):
        """Draw a sleek, sliding/scrolling capsule speech bubble for the current track."""
        if self.mute_alerts:
            return
            
        t = self.tick
        track = self.track_name
        
        # Clean track name of common Spotify suffixes
        for suffix in [" - Spotify Free", " - Spotify Premium", " - Spotify"]:
            if track.endswith(suffix):
                track = track[:-len(suffix)]
                
        # Scroll track title if it is long
        if len(track) > 12:
            padded = track + "   •   "
            shift = (t // 8) % len(padded)
            display_text = (padded + padded)[shift : shift + 12]
        else:
            display_text = track
            
        display_text = "♫ " + display_text
        
        # Bubble position floating bobbing
        by = 14 + math.sin(t * 0.2) * 3
        
        # Draw capsule border (neon green)
        self.canvas.create_line(cx - 32, by, cx + 32, by, fill="#1DB954", width=16, capstyle="round")
        # Draw capsule interior (dark grey/black)
        self.canvas.create_line(cx - 32, by, cx + 32, by, fill="#191414", width=13, capstyle="round")
        
        # Draw capsule pointer tail
        self.canvas.create_polygon(cx - 4, by + 7, cx + 4, by + 7, cx, by + 12, fill="#1DB954", outline="")
        self.canvas.create_polygon(cx - 2, by + 7, cx + 2, by + 7, cx, by + 10, fill="#191414", outline="")
        
        # Text inside capsule
        self.canvas.create_text(cx, by, text=display_text, fill="#1ED760", font=("Arial", 7, "bold"))

    def draw_spotify_skin(self, cx, cy, sx, sy):
        t = self.tick
        
        # Snoring particles in sleeping state
        if self.state == "sleeping":
            self.draw_snores(cx, cy)
            
        # Walk foot bounce
        leg_sway = 0.0
        if self.state == "walking":
            leg_sway = math.sin(t * 0.25) * 8 * sy
            cy -= abs(math.sin(t * 0.25)) * 3 * sy
            
        # Spawn music notes if playing
        is_playing = (self.activity_state == "playing")
        if is_playing and t % 15 == 0:
            self.spawn_music_note(cx, cy)
            
        # Spawn giggle particles if grabbed/dragging
        if self.is_dragging and t % 8 == 0:
            self.spawn_giggle_particle(cx, cy)
            
        # Giggle wiggle/shake if grabbed/dragging
        if self.is_dragging:
            cx += math.sin(t * 1.8) * 5 * sx
            cy += math.cos(t * 2.2) * 3 * sy
            
        # Draw legs
        if self.state != "climbing":
            self.canvas.create_rectangle(cx - 10 * sx, cy + 14 * sy, cx - 4 * sx, cy + (21 + leg_sway) * sy, fill="#1DB954", outline="#191414", width=1)
            self.canvas.create_rectangle(cx + 4 * sx, cy + 14 * sy, cx + 10 * sx, cy + (21 - leg_sway) * sy, fill="#1DB954", outline="#191414", width=1)
        else:
            # Climbing legs
            self.canvas.create_rectangle(cx - 18 * sx, cy - 8 * sy, cx - 23 * sx, cy - 3 * sy, fill="#1DB954", outline="#191414", width=1)
            self.canvas.create_rectangle(cx - 18 * sx, cy + 5 * sy, cx - 23 * sx, cy + 10 * sy, fill="#1DB954", outline="#191414", width=1)

        # Bobbing/dancing logic if playing music
        if is_playing:
            cy += math.sin(t * 0.6) * 4 * sy
            cx += math.cos(t * 0.3) * 2 * sx

        # Headphones Band (drawn behind body)
        self.canvas.create_arc(cx - 19 * sx, cy - 20 * sy, cx + 19 * sx, cy + 10 * sy, start=20, extent=140, style="arc", outline="#1DB954", width=3)

        # Main Body (Sleek dark circular robot)
        self.canvas.create_oval(cx - 16 * sx, cy - 16 * sy, cx + 16 * sx, cy + 16 * sy, fill="#191414", outline="#1DB954", width=3)
        
        # Ear pads for headphones (drawn on top of body sides)
        self.canvas.create_oval(cx - 21 * sx, cy - 8 * sy, cx - 15 * sx, cy + 8 * sy, fill="#1ED760", outline="#1DB954", width=1)
        self.canvas.create_oval(cx + 15 * sx, cy - 8 * sy, cx + 21 * sx, cy + 8 * sy, fill="#1ED760", outline="#1DB954", width=1)

        # Visualizer Eyes
        eye_y = cy - 2 * sy
        # Left eye
        for i, offset in enumerate([-2, 0, 2]):
            if is_playing:
                h = 6 + math.sin(t * 0.4 + i * 1.5) * 4
            else:
                h = 4 + math.sin(t * 0.1 + i * 1.0) * 1.5
            h = max(2, h) * sy
            bx = cx - 8 * sx + offset * 2.5 * sx
            self.canvas.create_rectangle(bx - 0.8 * sx, eye_y - h/2, bx + 0.8 * sx, eye_y + h/2, fill="#1ED760", outline="")
            
        # Right eye
        for i, offset in enumerate([-2, 0, 2]):
            if is_playing:
                h = 6 + math.cos(t * 0.4 + i * 1.5) * 4
            else:
                h = 4 + math.cos(t * 0.1 + i * 1.0) * 1.5
            h = max(2, h) * sy
            bx = cx + 8 * sx + offset * 2.5 * sx
            self.canvas.create_rectangle(bx - 0.8 * sx, eye_y - h/2, bx + 0.8 * sx, eye_y + h/2, fill="#1ED760", outline="")

        # Glowing green mouth arc (smile)
        self.canvas.create_arc(cx - 6 * sx, cy + 2 * sy, cx + 6 * sx, cy + 8 * sy, start=200, extent=140, style="arc", outline="#1ED760", width=2)
        
        # Now Playing bubble
        if is_playing and hasattr(self, 'track_name') and self.track_name:
            self.draw_now_playing_bubble(cx, cy)


# ==============================================================================
# DEVELOPER PAL REGISTRY SYSTEM
# ==============================================================================
# Developers can easily extend Agent Pal by adding new companions (e.g. Teams,
# WhatsApp, Chrome) here. Define your skin drawing function and register it!
# ==============================================================================

# ------------------------------------------------------------------------------
# Custom Mascot Skin Drawing Functions
# ------------------------------------------------------------------------------
def draw_whatsapp_skin(buddy, cx, cy, sx, sy):
    t = buddy.tick
    is_unread = (getattr(buddy, 'activity_state', None) == "unread")
    
    # Body bobbing/dancing if unread message (excited jumping/bobbing)
    leg_sway = 0
    if is_unread:
        cy += math.sin(t * 0.8) * 5 * sy
        leg_sway = math.sin(t * 0.8) * 4
    else:
        # Gentle floating breath
        cy += math.sin(t * 0.1) * 2 * sy
        
    # Draw legs
    if buddy.state != "climbing":
        buddy.canvas.create_rectangle(cx - 10 * sx, cy + 14 * sy, cx - 4 * sx, cy + (21 + leg_sway) * sy, fill="#128C7E", outline="#075E54", width=1)
        buddy.canvas.create_rectangle(cx + 4 * sx, cy + 14 * sy, cx + 10 * sx, cy + (21 - leg_sway) * sy, fill="#128C7E", outline="#075E54", width=1)
        
    # Main Body: WhatsApp Green circle
    buddy.canvas.create_oval(cx - 16 * sx, cy - 16 * sy, cx + 16 * sx, cy + 16 * sy, fill="#25D366", outline="#075E54", width=3)
    
    # White inner circle/shield
    buddy.canvas.create_oval(cx - 9 * sx, cy - 9 * sy, cx + 9 * sx, cy + 9 * sy, fill="white", outline="")
    
    # Speech bubble tail in WhatsApp logo style (little triangle on bottom-left)
    buddy.canvas.create_polygon(
        cx - 8 * sx, cy + 4 * sy,
        cx - 12 * sx, cy + 10 * sy,
        cx - 2 * sx, cy + 7 * sy,
        fill="white", outline=""
    )
    
    # Green phone receiver arc inside
    buddy.canvas.create_arc(cx - 5 * sx, cy - 5 * sy, cx + 5 * sx, cy + 5 * sy, start=120, extent=120, style="arc", outline="#25D366", width=3)
    
    # Eyes: Sleek messaging bubble shape eyes
    eye_y = cy - 4 * sy
    buddy.canvas.create_oval(cx - 10 * sx, eye_y - 2.5 * sy, cx - 5 * sx, eye_y + 2.5 * sy, fill="#075E54", outline="")
    buddy.canvas.create_oval(cx + 5 * sx, eye_y - 2.5 * sy, cx + 10 * sx, eye_y + 2.5 * sy, fill="#075E54", outline="")
    
    # Draw unread badge if unread message
    if is_unread:
        # Small red badge at top right
        buddy.canvas.create_oval(cx + 10 * sx, cy - 20 * sy, cx + 22 * sx, cy - 8 * sy, fill="#FF2D55", outline="white", width=1)
        # Small white exclamation in badge
        buddy.canvas.create_text(cx + 16 * sx, cy - 14 * sy, text="!", fill="white", font=("Arial", 8, "bold"))
        
    # Spawn text particles
    if is_unread and t % 20 == 0:
        import random
        msgs = ["💬", "Hi", "Hey", "Yo", "Hello", "📱", "text me", "new message"]
        colors = ["#25D366", "#128C7E", "#E2F4EB"]
        buddy.music_notes.append({
            'x': cx + random.uniform(-10, 10),
            'y': cy - 15 * sy,
            'vx': random.uniform(-0.8, 0.8),
            'vy': random.uniform(-1.5, -0.6),
            'size': random.randint(11, 15),
            'char': random.choice(msgs),
            'color': random.choice(colors),
            'age': 0,
            'max_age': random.randint(30, 45)
        })

def draw_teams_skin(buddy, cx, cy, sx, sy):
    t = buddy.tick
    is_meeting = (getattr(buddy, 'activity_state', None) == "meeting")
    
    # Teams body sway
    leg_sway = 0
    if is_meeting:
        # Fast anxious meeting vibration or swaying
        cy += math.sin(t * 0.4) * 3 * sy
        cx += math.cos(t * 0.4) * 2 * sx
        leg_sway = math.sin(t * 0.4) * 3
    else:
        cy += math.sin(t * 0.1) * 1.5 * sy
        
    # Draw legs
    if buddy.state != "climbing":
        buddy.canvas.create_rectangle(cx - 10 * sx, cy + 14 * sy, cx - 4 * sx, cy + (21 + leg_sway) * sy, fill="#2C3075", outline="#1F2251", width=1)
        buddy.canvas.create_rectangle(cx + 4 * sx, cy + 14 * sy, cx + 10 * sx, cy + (21 - leg_sway) * sy, fill="#2C3075", outline="#1F2251", width=1)

    # Teams Purple Round-Square Body
    buddy.canvas.create_oval(cx - 16 * sx, cy - 16 * sy, cx + 16 * sx, cy + 16 * sy, fill="#464EB8", outline="#2C3075", width=3)
    
    # White interlocking figures / logo details
    buddy.canvas.create_oval(cx - 11 * sx, cy - 8 * sy, cx - 1 * sx, cy + 8 * sy, fill="#5B60C4", outline="")
    buddy.canvas.create_rectangle(cx - 1 * sx, cy - 10 * sy, cx + 11 * sx, cy + 10 * sy, fill="white", outline="")
    buddy.canvas.create_text(cx + 5 * sx, cy, text="T", fill="#464EB8", font=("Arial", 11, "bold"))
    
    # Eyes: Glowing blue/purple corporate eyes
    eye_y = cy - 3 * sy
    eye_color = "#E2E4F6" if not is_meeting else "#FF3B30"
    buddy.canvas.create_oval(cx - 7 * sx, eye_y - 2 * sy, cx - 3 * sx, eye_y + 2 * sy, fill=eye_color, outline="")
    buddy.canvas.create_oval(cx - 13 * sx, eye_y - 2 * sy, cx - 9 * sx, eye_y + 2 * sy, fill=eye_color, outline="")
    
    # Draw "Recording / In-meeting" red dot if in a meeting
    if is_meeting:
        buddy.canvas.create_oval(cx + 10 * sx, cy - 20 * sy, cx + 18 * sx, cy - 12 * sy, fill="#FF3B30", outline="white", width=1)
        
    # Spawn text particles
    if is_meeting and t % 20 == 0:
        import random
        teams_chars = ["💼", "Call", "Meet", "Join", "Sync", "📅", "Ping", "Teams"]
        colors = ["#464EB8", "#5B60C4", "#E2E4F6"]
        buddy.music_notes.append({
            'x': cx + random.uniform(-10, 10),
            'y': cy - 15 * sy,
            'vx': random.uniform(-0.8, 0.8),
            'vy': random.uniform(-1.5, -0.6),
            'size': random.randint(11, 15),
            'char': random.choice(teams_chars),
            'color': random.choice(colors),
            'age': 0,
            'max_age': random.randint(30, 45)
        })


class PalDefinition:
    def __init__(self, keyword, mascot_type, draw_skin_fn, 
                 process_filter_fn=None, status_check_fn=None, 
                 on_single_click_fn=None, on_double_click_fn=None,
                 on_triple_click_fn=None,
                 reacts_to_bugs=True, show_agent_alerts=True,
                 strict_name_match=False):
        """
        Defines a Pal Companion.
        
        :param keyword: The keyword to search for in running processes.
        :param mascot_type: Unique mascot type identifier.
        :param draw_skin_fn: Function to draw the buddy on Tkinter canvas. Signature: fn(buddy, cx, cy, sx, sy)
        :param process_filter_fn: Custom filter to isolate main process from sub-processes. Signature: fn(name, cmdline, cmdline_str) -> bool
        :param status_check_fn: Heuristics to update buddy state. Signature: fn(buddy) -> bool (returns True if alive)
        :param on_single_click_fn: Single-click callback. Signature: fn(buddy)
        :param on_double_click_fn: Double-click callback. Signature: fn(buddy)
        :param on_triple_click_fn: Triple-click callback. Signature: fn(buddy)
        :param reacts_to_bugs: Whether the buddy chases spawned code bugs.
        :param show_agent_alerts: Whether to display CLI alert (!) and success (✔) bubbles.
        :param strict_name_match: If True, only matches if keyword is in the process image name (ignores arguments).
        """
        self.keyword = keyword
        self.mascot_type = mascot_type
        self.draw_skin_fn = draw_skin_fn
        self.process_filter_fn = process_filter_fn
        self.status_check_fn = status_check_fn
        self.on_single_click_fn = on_single_click_fn
        self.on_double_click_fn = on_double_click_fn
        self.on_triple_click_fn = on_triple_click_fn
        self.reacts_to_bugs = reacts_to_bugs
        self.show_agent_alerts = show_agent_alerts
        self.strict_name_match = strict_name_match

PAL_REGISTRY = {}

def register_pal(pal_def):
    """Register a Pal Definition globally in Agent Pal."""
    PAL_REGISTRY[pal_def.keyword] = pal_def

# ----------------------------------------------------
# 1. Custom Process Filters
# ----------------------------------------------------
def filter_claude_process(name, cmdline, cmdline_str):
    if 'node' in name:
        return any(term in cmdline_str for term in ['claude-code', 'claude.js', 'claude.exe'])
    return 'claude' in name

def filter_antigravity_process(name, cmdline, cmdline_str):
    if 'python' in name:
        return any(term in cmdline_str for term in ['antigravity', 'agy'])
    return 'antigravity' in name or 'agy' in name

def filter_spotify_process(name, cmdline, cmdline_str):
    if 'spotify' in name:
        return not any('--type=' in arg.lower() for arg in cmdline)
    return False

# ----------------------------------------------------
# 2. Custom Status Checkers
# ----------------------------------------------------
def check_spotify_status(buddy):
    if not buddy.agent_window_hwnd or not win32gui.IsWindow(buddy.agent_window_hwnd):
        buddy.find_agent_window()
    
    is_playing = False
    track = ""
    if buddy.agent_window_hwnd:
        try:
            title = win32gui.GetWindowText(buddy.agent_window_hwnd)
            if title and title.lower() not in ["spotify", "spotify free", "spotify premium"]:
                is_playing = True
                track = title
        except Exception:
            pass
    
    buddy.activity_state = "playing" if is_playing else None
    buddy.track_name = track
    buddy.alert_active = False
    return True

# ----------------------------------------------------
# 3. Custom Click Actions
# ----------------------------------------------------
def on_spotify_single_click(buddy):
    import win32api
    import win32con
    # VK_MEDIA_PLAY_PAUSE = 0xB3
    win32api.keybd_event(0xB3, 0, 0, 0)
    win32api.keybd_event(0xB3, 0, win32con.KEYEVENTF_KEYUP, 0)
    print("Spotify Buddy: Sent Media Play/Pause")

def on_spotify_double_click(buddy):
    import win32api
    import win32con
    # VK_MEDIA_PREV_TRACK = 0xB1
    win32api.keybd_event(0xB1, 0, 0, 0)
    win32api.keybd_event(0xB1, 0, win32con.KEYEVENTF_KEYUP, 0)
    print("Spotify Buddy: Sent Media Previous Track")

def on_spotify_triple_click(buddy):
    import win32api
    import win32con
    # VK_MEDIA_NEXT_TRACK = 0xB0
    win32api.keybd_event(0xB0, 0, 0, 0)
    win32api.keybd_event(0xB0, 0, win32con.KEYEVENTF_KEYUP, 0)
    print("Spotify Buddy: Sent Media Next Track")

# ----------------------------------------------------
# Process Filters for Teams & WhatsApp
# ----------------------------------------------------
def filter_whatsapp_process(name, cmdline, cmdline_str):
    if 'whatsapp' in name:
        return not any('--type=' in arg.lower() for arg in cmdline)
    return False

def filter_teams_process(name, cmdline, cmdline_str):
    if 'teams' in name:
        # Microsoft Teams has sub-processes with --type= or --process_type=
        is_sub = any(term in arg.lower() for arg in cmdline for term in ['--type=', '--process_type=', '--service-sandbox-type='])
        return not is_sub
    return False

# ----------------------------------------------------
# Status Checkers for Teams & WhatsApp
# ----------------------------------------------------
def check_whatsapp_status(buddy):
    if not buddy.agent_window_hwnd or not win32gui.IsWindow(buddy.agent_window_hwnd):
        buddy.find_agent_window()
    
    unread = False
    title = ""
    if buddy.agent_window_hwnd:
        try:
            title = win32gui.GetWindowText(buddy.agent_window_hwnd)
            if title and title.strip().startswith("("):
                unread = True
        except Exception:
            pass
            
    buddy.activity_state = "unread" if unread else None
    buddy.alert_active = False
    return True

def check_teams_status(buddy):
    if not buddy.agent_window_hwnd or not win32gui.IsWindow(buddy.agent_window_hwnd):
        buddy.find_agent_window()
        
    in_meeting = False
    title = ""
    if buddy.agent_window_hwnd:
        try:
            title = win32gui.GetWindowText(buddy.agent_window_hwnd)
            if title and any(word in title.lower() for word in ["meeting", "call", "in-call", "sync"]):
                in_meeting = True
        except Exception:
            pass
            
    buddy.activity_state = "meeting" if in_meeting else None
    buddy.alert_active = False
    return True

# Click Action for Teams & WhatsApp
def on_app_single_click(buddy):
    buddy.focus_agent_window()

# ----------------------------------------------------
# 4. Standard Registry Setup
# ----------------------------------------------------
register_pal(PalDefinition(
    keyword="claude",
    mascot_type="claude",
    draw_skin_fn=BaseBuddyWindow.draw_claude_skin,
    process_filter_fn=filter_claude_process
))

register_pal(PalDefinition(
    keyword="claudecode",
    mascot_type="claude",
    draw_skin_fn=BaseBuddyWindow.draw_claude_skin,
    process_filter_fn=filter_claude_process
))

register_pal(PalDefinition(
    keyword="antigravity",
    mascot_type="antigravity",
    draw_skin_fn=BaseBuddyWindow.draw_antigravity_skin,
    process_filter_fn=filter_antigravity_process
))

register_pal(PalDefinition(
    keyword="agy",
    mascot_type="antigravity",
    draw_skin_fn=BaseBuddyWindow.draw_antigravity_skin,
    process_filter_fn=filter_antigravity_process
))

register_pal(PalDefinition(
    keyword="codex",
    mascot_type="generic",
    draw_skin_fn=BaseBuddyWindow.draw_generic_skin
))

register_pal(PalDefinition(
    keyword="spotify",
    mascot_type="spotify",
    draw_skin_fn=BaseBuddyWindow.draw_spotify_skin,
    process_filter_fn=filter_spotify_process,
    status_check_fn=check_spotify_status,
    on_single_click_fn=on_spotify_single_click,
    on_double_click_fn=on_spotify_double_click,
    on_triple_click_fn=on_spotify_triple_click,
    reacts_to_bugs=False,
    show_agent_alerts=False,
    strict_name_match=True
))

register_pal(PalDefinition(
    keyword="whatsapp",
    mascot_type="whatsapp",
    draw_skin_fn=draw_whatsapp_skin,
    process_filter_fn=filter_whatsapp_process,
    status_check_fn=check_whatsapp_status,
    on_single_click_fn=on_app_single_click,
    on_double_click_fn=on_app_single_click,
    reacts_to_bugs=False,
    show_agent_alerts=False,
    strict_name_match=True
))

register_pal(PalDefinition(
    keyword="teams",
    mascot_type="teams",
    draw_skin_fn=draw_teams_skin,
    process_filter_fn=filter_teams_process,
    status_check_fn=check_teams_status,
    on_single_click_fn=on_app_single_click,
    on_double_click_fn=on_app_single_click,
    reacts_to_bugs=False,
    show_agent_alerts=False,
    strict_name_match=True
))


class AgentBuddy(BaseBuddyWindow):
    def __init__(self, root, pid, name, keyword):
        self.pid = pid
        self.name = name
        self.keyword = keyword
        
        # Select mascot skin based on registry
        pal_def = PAL_REGISTRY.get(keyword)
        if pal_def:
            mascot_type = pal_def.mascot_type
        else:
            mascot_type = "generic"
            
        super().__init__(root, mascot_type)
        
        # Process handle
        try:
            self.proc = psutil.Process(self.pid)
        except Exception:
            self.proc = None
            
        self.agent_window_hwnd = None
        self.find_agent_window()
        
        # Move buddy to the monitor where the agent terminal is located
        if self.agent_window_hwnd:
            rect = self.get_monitor_rect_from_window(self.agent_window_hwnd)
            if rect:
                left, top, right, bottom = rect
                self.floor_y = bottom - self.height
                self.x = random.randint(left + 100, right - 200)
                self.y = self.floor_y
                self.update_geometry()
                
        # Alert check states
        self.cpu_history = []
        self.was_busy = False
        self.success_timer = 0
        
        # Context menu additions
        self.menu.insert_command(0, label=f"Focus Terminal ({self.name})", command=self.focus_agent_window)
        

        
    def find_agent_window(self):
        """Find the visible window hosting the console of the agent process."""
        import ctypes
        import win32console
        import win32gui
        
        # 1. Primary Method: AttachConsole + GetConsoleWindow (Handles Windows Terminal tabs natively!)
        try:
            # Free our console first
            try:
                win32console.FreeConsole()
            except Exception:
                pass
                
            win32console.AttachConsole(self.pid)
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            
            if hwnd and win32gui.IsWindow(hwnd):
                # Under Windows Terminal, the console window is a hidden child of WindowsTerminal.exe
                parent = win32gui.GetParent(hwnd)
                if parent and win32gui.IsWindowVisible(parent):
                    self.agent_window_hwnd = parent
                    print(f"  [Console Attach Success] HWND={parent} (Parent of Console HWND={hwnd})")
                elif win32gui.IsWindowVisible(hwnd):
                    self.agent_window_hwnd = hwnd
                    print(f"  [Console Attach Success] HWND={hwnd}")
                    
            win32console.FreeConsole()
        except Exception as e:
            print(f"  AttachConsole window check failed for PID {self.pid}: {e}")
            try:
                win32console.FreeConsole()
            except Exception:
                pass
                
        if self.agent_window_hwnd and win32gui.IsWindow(self.agent_window_hwnd):
            return
            
        # 2. Fallback 1: Process Tree Search
        print(f"  Console attachment failed. Trying Process Tree Search for PID {self.pid}...")
        try:
            pids_to_check = {self.pid}
            try:
                for child in self.proc.children(recursive=True):
                    pids_to_check.add(child.pid)
            except Exception:
                pass
                
            try:
                curr = self.proc
                while curr:
                    parent = curr.parent()
                    if parent:
                        pname = parent.name().lower()
                        if pname in ['explorer.exe', 'services.exe', 'lsass.exe']:
                            break
                        pids_to_check.add(parent.pid)
                        curr = parent
                    else:
                        break
            except Exception:
                pass
                
            hwnds = []
            def callback(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    _, w_pid = win32process.GetWindowThreadProcessId(hwnd)
                    if w_pid in pids_to_check:
                        title = win32gui.GetWindowText(hwnd)
                        if title:
                            hwnds.append((hwnd, title, w_pid))
                return True
                
            win32gui.EnumWindows(callback, None)
            
            if hwnds:
                for hwnd, title, w_pid in hwnds:
                    t_lower = title.lower()
                    if self.keyword in t_lower or (self.keyword == "spotify" and len(title.strip()) > 0) or any(term in t_lower for term in ["terminal", "cmd", "powershell", "bash"]):
                        self.agent_window_hwnd = hwnd
                        print(f"  [Tree Search Success] HWND={hwnd} Title='{title}'")
                        return
                self.agent_window_hwnd = hwnds[0][0]
                print(f"  [Tree Search Fallback] HWND={self.agent_window_hwnd}")
                return
        except Exception as e:
            print(f"  Tree search failed for PID {self.pid}: {e}")
            
        if self.agent_window_hwnd and win32gui.IsWindow(self.agent_window_hwnd):
            return
            
        # 3. Fallback 2: Search all windows by Title Match
        print(f"  Tree search failed. Trying Title Match search for keyword '{self.keyword}'...")
        matched_hwnds = []
        def title_callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                if self.keyword in title:
                    matched_hwnds.append(hwnd)
            return True
            
        win32gui.EnumWindows(title_callback, None)
        if matched_hwnds:
            self.agent_window_hwnd = matched_hwnds[0]
            print(f"  [Title Match Success] HWND={self.agent_window_hwnd}")
            
    def focus_agent_window(self):
        if not self.agent_window_hwnd or not win32gui.IsWindow(self.agent_window_hwnd):
            self.find_agent_window()
            
        if self.agent_window_hwnd:
            print(f"Focusing window handle: {self.agent_window_hwnd}")
            force_foreground_focus(self.agent_window_hwnd)
        else:
            print(f"Could not resolve window handle for PID {self.pid}")
            



            
    def check_agent_status(self):
        """Assess if the agent is waiting for input based on CPU and focus heuristic."""
        if not self.proc:
            return False
            
        try:
            # 1. Check if process is still running
            if not self.proc.is_running():
                return False
                
            pal_def = PAL_REGISTRY.get(self.keyword)
            if pal_def and pal_def.status_check_fn:
                return pal_def.status_check_fn(self)
            else:
                return self.default_check_agent_status()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def default_check_agent_status(self):
        """Default CLI agent CPU and focus heuristic status check."""
        try:
            foreground_hwnd = win32gui.GetForegroundWindow()
            is_focused = (foreground_hwnd == self.agent_window_hwnd)
            
            # If the terminal window is focused, immediately dismiss all notification bubbles
            if is_focused:
                self.success_timer = 0
                self.alert_active = False
                
            # 2. Get CPU usage (include children PIDs)
            cpu = self.proc.cpu_percent()
            try:
                for child in self.proc.children(recursive=True):
                    try:
                        cpu += child.cpu_percent()
                    except Exception:
                        pass
            except Exception:
                pass
                
            self.cpu_history.append(cpu)
            if len(self.cpu_history) > 5:
                self.cpu_history.pop(0)
                
            avg_cpu = sum(self.cpu_history) / len(self.cpu_history)
            
            # State transitions based on CPU
            if avg_cpu > 1.5:
                self.was_busy = True
                self.alert_active = False
                self.success_timer = 0
                if not self.activity_state:
                    self.activity_state = random.choice(["writing", "researching"])
                elif random.random() < 0.05:
                    self.activity_state = "writing" if self.activity_state == "researching" else "researching"
            else:
                self.activity_state = None
                
                # If we just went from busy -> idle
                if self.was_busy:
                    self.was_busy = False
                    # Only celebrate if we are not currently focused (meaning we finished in background)
                    if not is_focused:
                        self.success_timer = 8 # 8 seconds of green checkmark
                        # Play a jump celebration
                        self.vy = -10.0
                        self.state = "falling"
                        self.trigger_squash("launch", 6)
                        
            # Handle Success Timer countdown (runs once a second)
            if self.success_timer > 0:
                self.success_timer -= 1
                self.alert_active = False # don't show ! while celebrating ✔
            else:
                # Show alert (!) if idle (low CPU) AND window is NOT focused
                if avg_cpu < 1.0 and not is_focused:
                    self.alert_active = True
                else:
                    self.alert_active = False
                    
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False





class AgentCoordinator:
    def __init__(self, exit_when_idle=False):
        global coordinator_instance
        coordinator_instance = self
        
        self.exit_when_idle = exit_when_idle
        self.root = tk.Tk()
        self.root.withdraw() # Hide root window
        
        # Dimensions
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        
        # Get primary monitor work area for default floor_y
        left, top, right, bottom = (0, 0, self.screen_width, self.screen_height)
        try:
            import win32api
            monitors = win32api.EnumDisplayMonitors()
            if monitors:
                try:
                    info = win32api.GetMonitorInfo(monitors[0][0])
                    left, top, right, bottom = info['Work']
                except Exception:
                    left, top, right, bottom = monitors[0][2]
        except Exception:
            pass
        self.floor_y = bottom - 100 # Default buddy height is 100
        
        # Track spawned buddies: {pid: AgentBuddyInstance}
        self.active_agents = {}
        
        # Code bug tracking
        self.bugs = []
        
        # Collision timestamps to avoid double bounce physics loops
        self.last_bounce_time = {}
        
        # Tracking variables for idle auto-exit
        self.has_run_any_agent = False
        self.scan_count = 0
        
        # Start scanning and physics loops
        self.scan_processes_loop()
        self.physics_and_render_loop()
        
    def spawn_bug(self):
        floor_y = self.floor_y
        left, top, right, bottom = (0, 0, self.screen_width, self.screen_height)
        
        # If there are active agents, spawn on their active monitor
        if self.active_agents:
            active_buddy = list(self.active_agents.values())[0]
            floor_y = active_buddy.floor_y
            left, top, right, bottom = active_buddy.get_current_monitor_rect()
        else:
            # Fallback to primary monitor work area
            try:
                import win32api
                monitors = win32api.EnumDisplayMonitors()
                if monitors:
                    info = win32api.GetMonitorInfo(monitors[0][0])
                    left, top, right, bottom = info['Work']
            except Exception:
                pass
                
        bug = CodeBug(self.root, (left, top, right, bottom), floor_y)
        self.bugs.append(bug)
        print("Spawned a new Code Bug!")
        
    def squash_bug(self, bug):
        if bug in self.bugs:
            bug.win.destroy()
            self.bugs.remove(bug)
            print("Code Bug squashed!")
        
    def scan_processes_loop(self):
        """Scans process list for agent keywords every 1.5 seconds."""
        agent_keywords = list(PAL_REGISTRY.keys())
        current_pids = set()
        my_pid = os.getpid()
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    info = proc.info
                    pid = info['pid']
                    if pid == my_pid:
                        continue
                        
                    name = (info['name'] or '').lower()
                    cmdline = info['cmdline'] or []
                    cmdline_str = ' '.join(cmdline).lower()
                    
                    # Ignore common helper/subprocess executables immediately
                    if name in ['bash.exe', 'git.exe', 'cmd.exe', 'powershell.exe', 'conhost.exe', 
                                'curl.exe', 'ssh.exe', 'wsl.exe', 'openconsole.exe', 'tar.exe', 
                                'npm.exe', 'pip.exe', 'npx.exe', 'yarn.exe']:
                        continue
                        
                    # Exclude self running scripts
                    if 'agent_buddy.py' in cmdline_str or 'test_ui.py' in cmdline_str or 'test_monitor.py' in cmdline_str:
                        continue
                        
                    matched_kw = None
                    for kw in agent_keywords:
                        pal_def = PAL_REGISTRY.get(kw)
                        if pal_def and getattr(pal_def, 'strict_name_match', False):
                            if kw in name:
                                matched_kw = kw
                                break
                        else:
                            if kw in name or kw in cmdline_str:
                                matched_kw = kw
                                break
                                
                    if matched_kw:
                        # If there is a custom process filter callback in the registry, check it
                        pal_def = PAL_REGISTRY.get(matched_kw)
                        if pal_def and pal_def.process_filter_fn:
                            if not pal_def.process_filter_fn(name, cmdline, cmdline_str):
                                continue
                                
                        current_pids.add(pid)
                        # Spawn new buddy if we haven't tracked this PID yet
                        if pid not in self.active_agents:
                            print(f"Spawning buddy for new Agent PID {pid} ({info['name']})")
                            buddy = AgentBuddy(self.root, pid, info['name'], matched_kw)
                            self.active_agents[pid] = buddy
                            self.has_run_any_agent = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            print(f"Error scanning processes: {e}")
            
        # Clean up terminated agents
        terminated_pids = set(self.active_agents.keys()) - current_pids
        for pid in terminated_pids:
            print(f"Agent PID {pid} closed. Removing buddy.")
            self.active_agents[pid].win.destroy()
            del self.active_agents[pid]
            
        # Exit if exit_when_idle is True and no agents are running
        if self.exit_when_idle and not self.active_agents:
            # Wait a few scans on startup (approx 5 seconds) to allow initial process detection
            if self.has_run_any_agent or self.scan_count > 3:
                print("No active agents. Exiting coordinator as requested (--exit-when-idle).")
                self.root.destroy()
                sys.exit(0)
                
        self.scan_count += 1
        
        # Run scan again in 1500ms
        self.root.after(1500, self.scan_processes_loop)
        
    def physics_and_render_loop(self):
        """Update window positioning, coordinate collisions, and repaint canvasses."""
        
        # 1. Update status checks for agent buddies (only once every 30 frames ~1 second)
        if not hasattr(self, 'frame_count'):
            self.frame_count = 0
        self.frame_count += 1
        
        if self.frame_count % 30 == 0:
            for buddy in list(self.active_agents.values()):
                is_alive = buddy.check_agent_status()
                if not is_alive:
                    # Safeguard: if process closed before scanner caught it
                    buddy.win.destroy()
                    if buddy.pid in self.active_agents:
                        del self.active_agents[buddy.pid]
                        
        # 2. Get list of all buddies to run collisions
        buddies = list(self.active_agents.values())
        
        # 3. Update physics for all individual buddies
        for buddy in buddies:
            buddy.update_physics()
            
        # 4. Handle buddy-to-buddy collisions
        now = time.time()
        for i in range(len(buddies)):
            for j in range(i + 1, len(buddies)):
                b1 = buddies[i]
                b2 = buddies[j]
                
                # Skip if either is sleeping, dragging, or paused
                if b1.state == "sleeping" or b2.state == "sleeping":
                    continue
                if b1.is_dragging or b2.is_dragging or b1.paused or b2.paused:
                    continue
                    
                # Skip if not on the same vertical level (only collide on floor/walking)
                if abs(b1.y - b2.y) > 30:
                    continue
                    
                # Calculate horizontal overlap
                dist_x = abs(b1.x - b2.x)
                overlap_limit = 70.0
                
                if dist_x < overlap_limit:
                    # Check cooldown
                    pair_key = tuple(sorted([id(b1), id(b2)]))
                    last_time = self.last_bounce_time.get(pair_key, 0)
                    if now - last_time < BOUNCE_COOLDOWN:
                        continue
                        
                    self.last_bounce_time[pair_key] = now
                    
                    # 50% chance to leap/jump over each other to cross instead of bouncing!
                    if random.random() < 0.5:
                        # Decide who jumps
                        jumper = b1 if random.random() < 0.5 else b2
                        other = b2 if jumper is b1 else b1
                        
                        jumper.vy = -12.0 # Leap!
                        jumper.vx = jumper.direction * 5.0 # Fly forward in current direction to cross
                        jumper.state = "falling"
                        jumper.trigger_squash("launch", 6)
                        jumper.spawn_dust_cloud(jumper.x + jumper.width/2, jumper.y + jumper.height - 10)
                        
                        # The other buddy squashes slightly in reaction
                        other.trigger_squash("land", 4)
                        print(f"Collision: {jumper.mascot_type} jumped over {other.mascot_type} to cross!")
                        continue
                    
                    # Bumper bounce - always reverse directions and travel away
                    if b1.x < b2.x:
                        b1.direction = -1
                        b2.direction = 1
                    else:
                        b1.direction = 1
                        b2.direction = -1
                        
                    b1.vx = b1.direction * 1.8
                    b1.trigger_squash("land", 5)
                    
                    b2.vx = b2.direction * 1.8
                    b2.trigger_squash("land", 5)

                        
        # 5. Update and render active code bugs
        for bug in list(self.bugs):
            bug.update()
            
        # 6. Render/Paint all canvasses
        for buddy in buddies:
            buddy.render()
            
        # 33ms refresh (~30 FPS)
        self.root.after(33, self.physics_and_render_loop)
        
    def start(self):
        self.root.mainloop()

def main():
    import win32event
    import win32api
    import winerror
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Pal - Desktop Buddy for CLI Agents")
    parser.add_argument("--exit-when-idle", action="store_true", help="Exit completely when no active agents are running")
    args = parser.parse_args()
    
    # Win32 Named Mutex single-instance lock
    mutex_name = "Global\\AgentPalSingleInstanceMutex"
    try:
        # Keep the handle reference so it's not garbage collected
        mutex_handle = win32event.CreateMutex(None, False, mutex_name)
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            print("Agent Pal is already running. Exiting.")
            sys.exit(0)
    except Exception as e:
        print(f"Single instance check failed: {e}")
        
    coordinator = AgentCoordinator(exit_when_idle=args.exit_when_idle)
    coordinator.start()

if __name__ == "__main__":
    main()

