const MAP_INFO = {
    "starting_point": {"x": 300, "y": 300},
    "obstacles": [
        {"type": "wall", "x": 50, "y": 50, "width": 1500, "height": 15}, // top horizontal
        {"type": "wall", "x": 50, "y": 50, "width": 10, "height": 1100}, // left vertical
        {"type": "wall", "x": 50, "y": 1115, "width": 1500, "height": 15}, // bottom horizontal
        {"type": "wall", "x": 1550, "y": 50, "width": 10, "height": 1100}, // right vertical

        {"type": "wall", "x": 50, "y": 580, "width": 225, "height": 15}, // top-left-room bottom-wall left part 1
        {"type": "wall", "x": 400, "y": 580, "width": 300, "height": 15}, // top-left-room bottom-wall left part 2
        {"type": "wall", "x": 820, "y": 580, "width": 140, "height": 15}, // top-left-room bottom-wall left part 3
        {"type": "wall", "x": 940, "y": 50, "width": 15, "height": 100}, // top-left-room right-wall top part 1
        {"type": "wall", "x": 940, "y": 240, "width": 15, "height": 200}, // top-left-room right-wall top part 2
        {"type": "wall", "x": 940, "y": 520, "width": 15, "height": 80}, // top-left-room right-wall top part 3
    
        {"type": "wall", "x": 50, "y": 870, "width": 170, "height": 15}, // middle-left-room bottom-wall left part 1
        {"type": "wall", "x": 300, "y": 870, "width": 300, "height": 15}, // middle-left-room bottom-wall left part 2
        {"type": "wall", "x": 440, "y": 580, "width": 15, "height": 80}, // middle-left-room right-wall top part 1
        {"type": "wall", "x": 440, "y": 750, "width": 15, "height": 120}, // middle-left-room right-wall top part 2

        {"type": "wall", "x": 580, "y": 950, "width": 15, "height": 150}, // bottom-left-room right-wall

        {"type": "wall", "x": 1375, "y": 50, "width": 15, "height": 100}, // top-right-room left-wall top part 1
        {"type": "wall", "x": 1375, "y": 230, "width": 15, "height": 80}, // top-right-room left-wall top part 2
        {"type": "wall", "x": 1230, "y": 295, "width": 320, "height": 15}, // top-right-room bottom-wall

        {"type": "wall", "x": 950, "y": 295, "width": 150, "height": 15}, // top-middle-room bottom-wall left part 1
        {"type": "wall", "x": 1150, "y": 295, "width": 30, "height": 15}, // top-middle-room bottom-wall left part 2

        {"type": "wall", "x": 940, "y": 875, "width": 80, "height": 15}, // bottom-middle-room top-wall left part 1
        {"type": "wall", "x": 1170, "y": 875, "width": 150, "height": 15}, // bottom-middle-room top-wall left part 2
        {"type": "wall", "x": 940, "y": 880, "width": 15, "height": 230}, // bottom-middle-room left-wall
        {"type": "wall", "x": 1230, "y": 880, "width": 15, "height": 230}, // bottom-middle-room right-wall

        {"type": "wall", "x": 1470, "y": 875, "width": 100, "height": 15}, // bottom-right-room top-wall
    ]
}