from sys import stdout, stdin
import termios, tty
import math
from os import get_terminal_size

class Game:
    def __init__(self, player_x, player_y, player_angle):

        # Game Vars #
        # Set game dimensions to terminal dimensions
        self.VW, self.VH = [get_terminal_size().columns, get_terminal_size().lines]
        # Set wall height to terminal height
        self.WALL_HEIGHT = self.VH
        # Initialize empty screen
        self.screen = [''.join(['+' for i in range(self.VW)]) for row in range(self.VH)]
        # Game map defined by 16 bit integers
        self.MAP = [
            0b1111111111111111,
            0b1010001000000001,
            0b1010011000011001,
            0b1000000000011001,
            0b1000011111000011,
            0b1100001100000111,
            0b1100000000001011,
            0b1111111111111111,   
        ]
        
        # Player Vars #
        # Player position and angle passed on game init
        self.player_x = player_x
        self.player_y = player_y
        self.player_angle = player_angle
        # 90 degree (pi/2 radian) FOV
        self.FOV = math.pi / 2.7
        self.HALF_FOV = self.FOV / 2
        self.STEP_SIZE = 0.08 # Essentially player speed
        # Angle between each raycast
        # Divinding FOV by viewport width means there is one raycast corresponding
        # each column in the screen
        self.ANGLE_STEP = self.FOV / self.VW

    def getch(self):
        '''Set terminal to cbreak mode and listen for single character inputs.'''
        fd = stdin.fileno()
        orig = termios.tcgetattr(fd)
        
        try:
            tty.setcbreak(fd)
            return stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSAFLUSH, orig)

    def update(self, key):
        '''Update screen based on key press.'''

        # Store player's position before update
        previous_position = (self.player_x, self.player_y)

        # Move player backwards and forewards
        if key == 'w':
            self.player_x += math.cos(self.player_angle) * self.STEP_SIZE
            self.player_y += -math.sin(self.player_angle) * self.STEP_SIZE # Y increases down so take the negative of sin
        elif key == 's':
            self.player_x -= math.cos(self.player_angle) * self.STEP_SIZE
            self.player_y -= -math.sin(self.player_angle) * self.STEP_SIZE
        # Rotate player view left and right
        elif key == 'd':
            self.player_angle -= self.STEP_SIZE
        elif key == 'a':
            self.player_angle += self.STEP_SIZE
        # Clear screen and quit game
        elif key == 'q':
            stdout.write('\033[2J\033[3J\033[H')
            exit(0)

        # Check if the new player position is in a wall.
        # If it is, reset to the previous position stored at the beginning
        if self.point_in_wall(self.player_x, self.player_y):
            self.player_x, self.player_y = previous_position
        
        # Draw all lines
        for x, wall_height in enumerate(self.get_view()):
            self.draw_line(int(x), int(wall_height[0]), wall_height[1])

    def distance(self, a: float, b: float) -> float:
        '''Returns distance between a and b.'''
        return math.sqrt(a**2 + b**2)

    def point_in_wall(self, x: float, y: float) -> bool:
        try:
            line = self.MAP[int(y)] # Row containing point
            # Creates a bitmask with a 1 at x, then applies it to `line`.
            # If there is a wall at x, the bitwise AND operation will return a non-zero integer.
            # If there is, it will return zero.
            return (line & (1 << abs(int(x) - 1))) != 0
        # Returns true if point is out of the map
        except IndexError:
            return True

    def draw_line(self, x, height, shadow):
        '''Draws line given an x position and a height. The `shadow` boolean determines the character used to draw the line.'''

        # Amount of space above and below line
        offset = math.floor((self.VH - height) / 2)
        
        new_screen = []
        for num, row in enumerate(self.screen):
            if num in range(offset + 1, self.VH - offset):
                new_string = row[:x] + ('#' if not shadow else '+') + row[x + 1:]
            else:
                new_string = row[:x] + ' ' + row[x + 1:]
            new_screen.append(new_string)
        
        self.screen = new_screen

    def refresh_screen(self):
        stdout.write('\033[2J\033[3J\033[H')
        stdout.write('\n'.join(self.screen))
        
    def get_view(self):
        '''Returns wall distance for each column on screen'''

        # Player angle is directly forwards, so edge of FOV is player angle + half FOV
        starting_angle = self.player_angle + self.HALF_FOV

        # Iterator with number of items equal to number of columns
        walls = [0] * self.VW
        for idx in range(len(walls)):
            # Move the angle by ANGLE_STEP each iteration
            angle = starting_angle - idx * self.ANGLE_STEP

            h_dist = self.horizontal_intersection(angle)
            v_dist = self.vertical_intersection(angle)
            min_dist, shadow = (h_dist, False) if (h_dist < v_dist) else (v_dist, True)

            height = int(self.WALL_HEIGHT / (min_dist * math.cos(angle - self.player_angle)))
            if height > self.VH:
                height = self.VH
            walls[idx] = (height, shadow)

        return walls

    def horizontal_intersection(self, angle: float) -> float:
        up = abs(math.floor(angle / math.pi) % 2.0) != 0.0

        first_y = math.ceil(self.player_y) - self.player_y if up else math.floor(self.player_y) - self.player_y
        first_x = -first_y / math.tan(angle)

        dy = 1.0 if up else -1.0
        dx = -dy / math.tan(angle)

        next_x = first_x
        next_y = first_y

        for _ in range(256):
            current_x = next_x + self.player_x
            current_y = next_y + self.player_y if up else next_y + self.player_y - 1.0

            if self.point_in_wall(current_x, current_y):
                break

            next_x += dx
            next_y += dy

        return self.distance(next_x, next_y)

    def vertical_intersection(self, angle: float) -> float:
        right = abs(math.floor((angle - math.pi / 2) / math.pi) % 2.0) != 0.0

        first_x = math.ceil(self.player_x) - self.player_x if right else math.floor(self.player_x) - self.player_x
        first_y = -math.tan(angle) * first_x

        dx = 1.0 if right else -1.0
        dy = dx * -math.tan(angle)

        next_x = first_x
        next_y = first_y

        for _ in range(256):
            current_x = next_x + self.player_x if right else next_x + self.player_x - 1.0
            current_y = next_y + self.player_y

            if self.point_in_wall(current_x, current_y):
                break

            next_x += dx
            next_y += dy

        return self.distance(next_x, next_y)

    def run(self):
        self.refresh_screen()
        while True:
            self.update(self.getch())
            self.refresh_screen()

game = Game(3.0, 3.0, 1.0)

game.run()
