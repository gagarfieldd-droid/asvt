import tkinter as tk
from tkinter import ttk, messagebox
from enum import Enum
from itertools import product
import math

# Цвета - розовая тема
COLORS = {
    'INPUT': '#FF6B6B', 'AND': '#4ECDC4', 'NAND': '#45B7D1',
    'OR': '#FFB8B8', 'NOR': '#FFD6A5', 'NOT': '#DDA0DD',
    'XOR': '#FFC3A0', 'OUTPUT': '#A0C4FF',
    'wire_on': '#FF6B9D', 'wire_off': '#C9ADA7',
    'canvas_bg': '#FFE6E6',
    'panel_bg': '#FFB7C5',
    'panel_text': '#5D576B',
    'selected': '#FF4D6D',
    'gate_outline': '#FF8FA3',
    'connector_bg': '#FF4D6D'
}
GATE_W, GATE_H = 100, 70
CONNECTOR_RADIUS = 12
GRID = 25

class GateType(Enum):
    INPUT = "INPUT";
    OUTPUT = "OUTPUT";
    AND = "AND"
    NAND = "NAND";
    OR = "OR";
    NOR = "NOR"
    NOT = "NOT";
    XOR = "XOR"

class Gate:
    _id = 0
    def __init__(self, gate_type, x, y):
        Gate._id += 1
        self.type = gate_type
        self.x, self.y = x, y
        self.inputs = 1 if gate_type in (GateType.INPUT, GateType.NOT, GateType.OUTPUT) else 2
        self.in_vals = [0] * self.inputs
        self.out_val = 0
        self.selected = False
        self.canvas_items = []
        self.connector_items = []
        self.name = f"{gate_type.value}_{Gate._id}"

    def bbox(self):
        return (self.x - GATE_W // 2, self.y - GATE_H // 2,
                self.x + GATE_W // 2, self.y + GATE_H // 2)

    def get_input_positions(self):
        if self.inputs == 1:
            return [(self.x - GATE_W // 2, self.y)]
        step = GATE_H / (self.inputs + 1)
        return [(self.x - GATE_W // 2, self.y - GATE_H // 2 + step * (i + 1))
                for i in range(self.inputs)]

    def get_output_position(self):
        return (self.x + GATE_W // 2, self.y)

    def contains(self, x, y):
        x0, y0, x1, y1 = self.bbox()
        return x0 <= x <= x1 and y0 <= y <= y1

    def get_connector_at(self, x, y):
        # Проверяем выход
        ox, oy = self.get_output_position()
        if math.hypot(x - ox, y - oy) <= CONNECTOR_RADIUS:
            return ('output', 0, (ox, oy))

        # Проверяем входы
        for i, (ix, iy) in enumerate(self.get_input_positions()):
            if math.hypot(x - ix, y - iy) <= CONNECTOR_RADIUS:
                return ('input', i, (ix, iy))
        return None

    def toggle(self):
        if self.type == GateType.INPUT:
            self.out_val = 1 - self.out_val
    def evaluate(self):
        if self.type == GateType.INPUT:
            return
        if self.type == GateType.AND:
            self.out_val = 1 if all(self.in_vals) else 0
        elif self.type == GateType.NAND:
            self.out_val = 0 if all(self.in_vals) else 1
        elif self.type == GateType.OR:
            self.out_val = 1 if any(self.in_vals) else 0
        elif self.type == GateType.NOR:
            self.out_val = 0 if any(self.in_vals) else 1
        elif self.type == GateType.NOT:
            self.out_val = 1 - self.in_vals[0]
        elif self.type == GateType.XOR:
            self.out_val = sum(self.in_vals) % 2
        elif self.type == GateType.OUTPUT:
            self.out_val = self.in_vals[0]

class Connection:
    def __init__(self, source, dest, dest_input):
        self.source = source
        self.dest = dest
        self.dest_input = dest_input
        self.line_item = None
        self.start_dot = None
        self.end_dot = None

class LogicStudio:
    def __init__(self, root):
        self.root = root
        self.root.title("Логические схемы")
        self.root.geometry("1600x1000")

        self.gates = []
        self.connections = []
        self.selected_gate = None
        self.dragging_gate = None
        self.drag_offset = (0, 0)
        self.pending_connection = None
        self.temp_line = None

        self.create_ui()
        self.bind_events()

    def create_ui(self):
        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left = tk.Frame(main, bg=COLORS['panel_bg'], width=180)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left.pack_propagate(False)

        tk.Label(left, text="Элементы", bg=COLORS['panel_bg'],
                 fg=COLORS['panel_text'], font=('Arial', 14, 'bold')).pack(pady=20)

        gate_frame = tk.Frame(left, bg=COLORS['panel_bg'])
        gate_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        gate_types = [
            ("INPUT", GateType.INPUT, COLORS['INPUT']),
            ("AND", GateType.AND, COLORS['AND']),
            ("NAND", GateType.NAND, COLORS['NAND']),
            ("OR", GateType.OR, COLORS['OR']),
            ("NOR", GateType.NOR, COLORS['NOR']),
            ("NOT", GateType.NOT, COLORS['NOT']),
            ("XOR", GateType.XOR, COLORS['XOR']),
            ("OUTPUT", GateType.OUTPUT, COLORS['OUTPUT'])
        ]
        for i, (text, gate_type, color) in enumerate(gate_types):
            btn = tk.Button(gate_frame, text=text, bg=color, fg='black',
                            font=('Arial', 10, 'bold'),
                            command=lambda gt=gate_type: self.add_gate(gt),
                            height=2, width=8, relief=tk.RAISED, bd=2)
            btn.grid(row=i // 2, column=i % 2, padx=5, pady=5, sticky='nsew')

        for i in range(4):
            gate_frame.grid_rowconfigure(i, weight=1)
        gate_frame.grid_columnconfigure(0, weight=1)
        gate_frame.grid_columnconfigure(1, weight=1)

        control_frame = tk.Frame(left, bg=COLORS['panel_bg'])
        control_frame.pack(fill=tk.X, padx=10, pady=20)

        tk.Button(control_frame, text="Запустить", bg='#FF8FA3', fg='white',
                  font=('Arial', 10), command=self.simulate,
                  relief=tk.RAISED).pack(fill=tk.X, pady=5)

        tk.Button(control_frame, text="Таблица истинности", bg='#FF8FA3', fg='white',
                  font=('Arial', 10), command=self.show_truth_table,
                  relief=tk.RAISED).pack(fill=tk.X, pady=5)

        tk.Button(control_frame, text="Очистить", bg='#FF8FA3', fg='white',
                  font=('Arial', 10), command=self.clear_all,
                  relief=tk.RAISED).pack(fill=tk.X, pady=5)

        canvas_frame = tk.Frame(main)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg=COLORS['canvas_bg'], highlightthickness=0)

        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        status = ttk.Frame(self.root)
        status.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)

        self.status_var = tk.StringVar(value="")
        self.summary_var = tk.StringVar(value="")

        ttk.Label(status, textvariable=self.status_var).pack(side=tk.LEFT)
        ttk.Label(status, textvariable=self.summary_var).pack(side=tk.RIGHT)

    def bind_events(self):
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)
        self.canvas.bind("<Button-3>", self.on_right_click)

    def add_gate(self, gate_type):
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width > 0 and canvas_height > 0:
            x = canvas_width // 2
            y = canvas_height // 2
        else:
            x, y = 400, 300

        gate = Gate(gate_type, x, y)
        self.gates.append(gate)
        self.draw_gate(gate)
        self.update_summary()

    def draw_gate(self, gate):
        for item in gate.canvas_items + gate.connector_items:
            self.canvas.delete(item)
        gate.canvas_items.clear()
        gate.connector_items.clear()

        x0, y0, x1, y1 = gate.bbox()

        shadow = self.canvas.create_rectangle(x0 + 3, y0 + 3, x1 + 3, y1 + 3,
                                              fill='#FFB7C5', outline='')
        gate.canvas_items.append(shadow)

        color = COLORS.get(gate.type.value, '#FFD6D6')
        outline = COLORS['selected'] if gate.selected else COLORS['gate_outline']
        width = 3 if gate.selected else 2

        rect = self.canvas.create_rectangle(x0, y0, x1, y1,
                                            fill=color, outline=outline,
                                            width=width)
        gate.canvas_items.append(rect)

        if gate.type in (GateType.INPUT, GateType.OUTPUT):
            text = f"{gate.type.value}\n{gate.out_val}"
        else:
            text = gate.type.value

        text_item = self.canvas.create_text(gate.x, gate.y, text=text,
                                            font=('Arial', 10, 'bold'), fill='#5D576B')
        gate.canvas_items.append(text_item)

        for px, py in gate.get_input_positions():
            conn = self.canvas.create_oval(px - CONNECTOR_RADIUS, py - CONNECTOR_RADIUS,
                                           px + CONNECTOR_RADIUS, py + CONNECTOR_RADIUS,
                                           fill=COLORS['connector_bg'], outline='white',
                                           width=2)
            gate.connector_items.append(conn)

            inner = self.canvas.create_oval(px - CONNECTOR_RADIUS // 2, py - CONNECTOR_RADIUS // 2,
                                            px + CONNECTOR_RADIUS // 2, py + CONNECTOR_RADIUS // 2,
                                            fill='white', outline='')
            gate.connector_items.append(inner)

        px, py = gate.get_output_position()
        conn = self.canvas.create_oval(px - CONNECTOR_RADIUS, py - CONNECTOR_RADIUS,
                                       px + CONNECTOR_RADIUS, py + CONNECTOR_RADIUS,
                                       fill=COLORS['connector_bg'], outline='white',
                                       width=2)
        gate.connector_items.append(conn)

        inner = self.canvas.create_oval(px - CONNECTOR_RADIUS // 2, py - CONNECTOR_RADIUS // 2,
                                        px + CONNECTOR_RADIUS // 2, py + CONNECTOR_RADIUS // 2,
                                        fill='white', outline='')
        gate.connector_items.append(inner)

        val_color = COLORS['wire_on'] if gate.out_val else COLORS['wire_off']
        val_item = self.canvas.create_oval(px - 10, py - 10, px + 10, py + 10,
                                           fill=val_color, outline=COLORS['gate_outline'],
                                           width=2)
        gate.canvas_items.append(val_item)

        for item in gate.canvas_items + gate.connector_items:
            self.canvas.tag_raise(item)

    def draw_connection(self, conn):
        if conn.line_item:
            self.canvas.delete(conn.line_item)
        if conn.start_dot:
            self.canvas.delete(conn.start_dot)
        if conn.end_dot:
            self.canvas.delete(conn.end_dot)

        src_x, src_y = conn.source.get_output_position()
        dst_x, dst_y = conn.dest.get_input_positions()[conn.dest_input]

        color = COLORS['wire_on'] if conn.source.out_val else COLORS['wire_off']
        width = 4 if conn.source.out_val else 3

        conn.line_item = self.canvas.create_line(src_x, src_y, dst_x, dst_y,
                                                 fill=color, width=width)

        conn.start_dot = self.canvas.create_oval(src_x - 4, src_y - 4, src_x + 4, src_y + 4,
                                                 fill=color, outline=color)
        conn.end_dot = self.canvas.create_oval(dst_x - 4, dst_y - 4, dst_x + 4, dst_y + 4,
                                               fill=color, outline=color)

        self.canvas.tag_lower(conn.line_item)
        self.canvas.tag_lower(conn.start_dot)
        self.canvas.tag_lower(conn.end_dot)

    def on_click(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        for gate in reversed(self.gates):
            connector_info = gate.get_connector_at(x, y)
            if connector_info:
                conn_type, index, pos = connector_info

                if conn_type == 'output':
                    self.start_connection(gate)
                    return
                elif conn_type == 'input':
                    if self.pending_connection:
                        self.finish_connection(gate, index)
                    return

        for gate in reversed(self.gates):
            if gate.contains(x, y):
                self.select_gate(gate)
                self.dragging_gate = gate
                self.drag_offset = (x - gate.x, y - gate.y)
                return

        self.deselect_all()
        if self.pending_connection:
            self.cancel_connection()

    def on_drag(self, event):
        if self.dragging_gate:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)

            grid_x = round((x - self.drag_offset[0]) / GRID) * GRID
            grid_y = round((y - self.drag_offset[1]) / GRID) * GRID

            self.dragging_gate.x, self.dragging_gate.y = grid_x, grid_y
            self.draw_gate(self.dragging_gate)
            self.update_all_connections()

        elif self.pending_connection and self.temp_line:
            x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            src_x, src_y = self.pending_connection.get_output_position()
            self.canvas.coords(self.temp_line, src_x, src_y, x, y)

    def on_release(self, event):
        self.dragging_gate = None

    def on_double_click(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        for gate in self.gates:
            if gate.contains(x, y) and gate.type == GateType.INPUT:
                gate.toggle()
                self.draw_gate(gate)
                self.simulate()
                break

    def on_right_click(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        for gate in self.gates:
            if gate.contains(x, y):
                self.delete_gate(gate)
                return

        for conn in self.connections:
            src_x, src_y = conn.source.get_output_position()
            dst_x, dst_y = conn.dest.get_input_positions()[conn.dest_input]

            if self.point_line_distance(x, y, src_x, src_y, dst_x, dst_y) < 10:
                self.delete_connection(conn)
                return

    def point_line_distance(self, px, py, x1, y1, x2, y2):
        line_len = math.hypot(x2 - x1, y2 - y1)
        if line_len == 0:
            return math.hypot(px - x1, py - y1)

        t = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / (line_len * line_len)
        t = max(0, min(1, t))

        proj_x = x1 + t * (x2 - x1)
        proj_y = y1 + t * (y2 - y1)

        return math.hypot(px - proj_x, py - proj_y)

    def start_connection(self, gate):
        self.pending_connection = gate
        src_x, src_y = gate.get_output_position()

        self.temp_line = self.canvas.create_line(src_x, src_y, src_x, src_y,
                                                 dash=(5, 2), width=2,
                                                 fill=COLORS['connector_bg'])

    def finish_connection(self, gate, input_idx):
        if self.pending_connection and self.pending_connection != gate:
            for conn in self.connections:
                if conn.dest == gate and conn.dest_input == input_idx:
                    self.cancel_connection()
                    return

            new_conn = Connection(self.pending_connection, gate, input_idx)
            self.connections.append(new_conn)
            self.draw_connection(new_conn)
            self.simulate()

        self.cancel_connection()

    def cancel_connection(self):
        if self.temp_line:
            self.canvas.delete(self.temp_line)
            self.temp_line = None
        self.pending_connection = None

    def select_gate(self, gate):
        self.deselect_all()
        gate.selected = True
        self.selected_gate = gate
        self.draw_gate(gate)

    def deselect_all(self):
        for gate in self.gates:
            gate.selected = False
            self.draw_gate(gate)
        self.selected_gate = None

    def simulate(self):
        if not self.gates:
            return

        for gate in self.gates:
            if gate.type != GateType.INPUT:
                gate.in_vals = [0] * gate.inputs

        changed = True
        passes = 0
        while changed and passes < 100:
            passes += 1
            changed = False

            for conn in self.connections:
                conn.dest.in_vals[conn.dest_input] = conn.source.out_val

            for gate in self.gates:
                if gate.type != GateType.INPUT:
                    old_val = gate.out_val
                    gate.evaluate()
                    if gate.out_val != old_val:
                        changed = True

        for gate in self.gates:
            self.draw_gate(gate)

        self.update_all_connections()
        self.update_summary()


    def update_all_connections(self):
        for conn in self.connections:
            self.draw_connection(conn)

    def update_summary(self):
        inputs = [g for g in self.gates if g.type == GateType.INPUT]
        outputs = [g for g in self.gates if g.type == GateType.OUTPUT]

        if inputs or outputs:
            in_text = ", ".join(f"{i}={g.out_val}" for i, g in enumerate(inputs))
            out_text = ", ".join(f"{i}={g.out_val}" for i, g in enumerate(outputs))
            self.summary_var.set(f"IN: {in_text or '--'} | OUT: {out_text or '--'}")
        else:
            self.summary_var.set("")

    def show_truth_table(self):
        inputs = [g for g in self.gates if g.type == GateType.INPUT]
        outputs = [g for g in self.gates if g.type == GateType.OUTPUT]

        if not inputs or not outputs:
            return

        win = tk.Toplevel(self.root)
        win.title("Таблица истинности")
        win.geometry("600x400")

        cols = [f"IN{i}" for i in range(len(inputs))] + [f"OUT{j}" for j in range(len(outputs))]
        tree = ttk.Treeview(win, columns=cols, show="headings", height=15)

        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=70, anchor=tk.CENTER)

        saved = [g.out_val for g in inputs]

        for combo in product([0, 1], repeat=len(inputs)):
            for g, v in zip(inputs, combo):
                g.out_val = v

            self.simulate()
            out_vals = [g.out_val for g in outputs]
            tree.insert("", tk.END, values=list(combo) + out_vals)

        for g, v in zip(inputs, saved):
            g.out_val = v
        self.simulate()

        scroll = ttk.Scrollbar(win, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def delete_selected(self):
        if self.selected_gate:
            self.delete_gate(self.selected_gate)

    def delete_gate(self, gate):
        conns_to_remove = []
        for conn in self.connections:
            if conn.source == gate or conn.dest == gate:
                conns_to_remove.append(conn)

        for conn in conns_to_remove:
            self.delete_connection(conn)

        self.gates.remove(gate)
        for item in gate.canvas_items + gate.connector_items:
            self.canvas.delete(item)

        if self.selected_gate == gate:
            self.deselect_all()

        self.update_summary()
        self.simulate()

    def delete_connection(self, conn):
        if conn.line_item:
            self.canvas.delete(conn.line_item)
        if conn.start_dot:
            self.canvas.delete(conn.start_dot)
        if conn.end_dot:
            self.canvas.delete(conn.end_dot)

        if conn in self.connections:
            self.connections.remove(conn)

    def clear_all(self):

        for gate in self.gates:
            for item in gate.canvas_items + gate.connector_items:
                self.canvas.delete(item)

        for conn in self.connections:
            if conn.line_item:
                self.canvas.delete(conn.line_item)
            if conn.start_dot:
                self.canvas.delete(conn.start_dot)
            if conn.end_dot:
                self.canvas.delete(conn.end_dot)

        self.gates.clear()
        self.connections.clear()
        self.deselect_all()
        self.summary_var.set("")


def main():
    root = tk.Tk()
    app = LogicStudio(root)
    root.mainloop()


if __name__ == "__main__":
    main()