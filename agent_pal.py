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
    def __init__(self, root, floor_y, screen_width):
        self.root = root
        self.width = 30
        self.height = 30
        self.floor_y = floor_y + BUDDY_HEIGHT - self.height  # Align to buddy's bottom/taskbar
        self.screen_width = screen_width
        
        self.x = random.randint(100, screen_width - 100)
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
        self.x += self.vx
        self.tick += 1
        
        # Crawl bounds
        if self.x <= 0:
            self.x = 0
            self.vx = -self.vx
            self.direction = 1
        elif self.x >= self.screen_width - self.width:
            self.x = self.screen_width - self.width
            self.vx = -self.vx
            self.direction = -1
            
        if random.random() < 0.02:
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
        
        # Event bindings
        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
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
        self.last_drag_time = time.time()
        self.drag_path = [(self.last_drag_time, self.x, self.y)]
        self.vx = 0
        self.vy = 0
        self.state = "idle"
        
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
            
            # Record track for throwing physics
            now = time.time()
            self.drag_path.append((now, self.x, self.y))
            if len(self.drag_path) > 10:
                self.drag_path.pop(0)
                
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
        if coordinator_instance and coordinator_instance.bugs and self.state in ["idle", "walking", "chasing"]:
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
                if abs(self.x - closest_bug.x) < 20 and abs(self.y - closest_bug.y) < 25:
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
        if self.mascot_type == "antigravity":
            self.draw_antigravity_skin(cx, cy, scale_x, scale_y)
        elif self.mascot_type == "claude":
            self.draw_claude_skin(cx, cy, scale_x, scale_y)
        else:
            self.draw_generic_skin(cx, cy, scale_x, scale_y)
            
        # Draw coding/research accessories
        if self.activity_state:
            self.draw_busy_accessories(cx, cy)
            
        # Render overlays
        if self.state == "happy":
            self.draw_happy_sparkles(cx, cy)
            
        if hasattr(self, 'success_timer') and self.success_timer > 0:
            self.draw_success_bubble(self.tick)
        elif self.alert_active:
            self.draw_alert_bubble(self.tick)
            
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


class AgentBuddy(BaseBuddyWindow):
    def __init__(self, root, pid, name, keyword):
        self.pid = pid
        self.name = name
        self.keyword = keyword
        
        # Select mascot skin based on keyword
        mascot_type = "generic"
        if keyword in ["antigravity", "agy"]:
            mascot_type = "antigravity"
        elif keyword in ["claude", "claudecode"]:
            mascot_type = "claude"
            
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
        
        # Double click to focus window binding
        self.canvas.bind("<Double-Button-1>", self.on_double_click)
        
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
                    if self.keyword in t_lower or any(term in t_lower for term in ["terminal", "cmd", "powershell", "bash"]):
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
            
    def on_double_click(self, event):
        self.focus_agent_window()


            
    def check_agent_status(self):
        """Assess if the agent is waiting for input based on CPU and focus heuristic."""
        if not self.proc:
            return False
            
        try:
            # 1. Check if process is still running
            if not self.proc.is_running():
                return False
                
            # Check window focus first
            foreground_hwnd = win32gui.GetForegroundWindow()
            is_focused = (foreground_hwnd == self.agent_window_hwnd)
            
            # If the terminal window is focused, immediately dismiss all notification bubbles
            if is_focused:
                self.success_timer = 0
                self.alert_active = False
                
            # 2. Get CPU usage (include children PIDs)
            # Querying process CPU is expensive, so this is called on a 1-second interval
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
        if self.active_agents:
            floor_y = list(self.active_agents.values())[0].floor_y
        bug = CodeBug(self.root, floor_y, self.screen_width)
        self.bugs.append(bug)
        print("Spawned a new Code Bug!")
        
    def squash_bug(self, bug):
        if bug in self.bugs:
            bug.win.destroy()
            self.bugs.remove(bug)
            print("Code Bug squashed!")
        
    def scan_processes_loop(self):
        """Scans process list for agent keywords every 1.5 seconds."""
        agent_keywords = ['claude', 'claudecode', 'antigravity', 'agy', 'codex']
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
                        
                    # Filter node and python interpreters to only match main agent processes
                    if name == 'node.exe':
                        is_claude_main = any(term in cmdline_str for term in ['claude-code', 'claude.js', 'claude.exe'])
                        if not is_claude_main:
                            continue
                    elif name == 'python.exe':
                        is_agy_main = any(term in cmdline_str for term in ['antigravity', 'agy'])
                        if not is_agy_main:
                            continue
                            
                    matched_kw = None
                    for kw in agent_keywords:
                        if kw in name or kw in cmdline_str:
                            matched_kw = kw
                            break

                            
                    if matched_kw:
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

