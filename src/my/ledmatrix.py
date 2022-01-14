from .font import LCD_FONT, proportional
from .micropython_dotstar import DotStar
from machine import SPI, Pin


class LedMatrix():
    clock_pin = 12 # green wire on my strip
    data_pin  = 13 # yellow wire on my strip
    empty_pin = 18 # nothing is connected 
    center_text = False
            
    spi = SPI(sck=Pin(clock_pin), mosi=Pin(data_pin), miso=Pin(empty_pin), baudrate=250000) # Configure SPI
    
    def __init__(self, width=8, height=1, cascaded=1, intesity=31):
        self.strip = DotStar(self.spi, width*height*cascaded, auto_write=False) # define my array of leds
        self.width = width
        self.height = height
        self.cascaded = cascaded
        self.intesity = intesity
        self.backcolor = (0,0,0)

    def clear(self, backcolor=None ):
        if not backcolor:
            backcolor = self.backcolor
        color = list(backcolor)
        color.append(self.intesity)
        color = tuple(color)
        for x in range(self.width*self.height*self.cascaded):
            self.strip[x] = color
        self.draw()
        
    def index_from_coordinates(self, x, y):
        if x >= self.width*self.cascaded or y >= self.height:
            return 0

        pos = 0
        if x>=self.width:
            cascade = x//self.width
            pos = self.width*self.height*cascade
            x = x-self.width*cascade
            
        pos += y * self.width + x
        return pos

    def point(self, xy, color):
        x, y = xy
        if x >= self.width*self.cascaded or y >= self.height:
            return
        color = list(color)
        color.append(self.intesity)
        color = tuple(color)
        
        pos = 0
        if x>=self.width:
            cascade = x//self.width
            pos = self.width*self.height*cascade
            x = x-self.width*cascade
            
        pos += y * self.width + x
        
        self.strip[pos] = color

    def draw(self):
        self.strip.show()

    def text(self, txt, color=(0xC0, 0xC0, 0xC0), font=proportional(LCD_FONT), start=(0,0)):

        # self.clear()

        x, y = start
        for ch in txt:
            # print('drawing ', ch)
            for byte in font[ord(ch)]:
                for j in range(8):
                    if byte & 0x01 > 0:
                        self.point((x, y + j), color=color)
                    else:
                        self.point((x, y + j), self.backcolor)
                    byte >>= 1
                x += 1
        
        # draw the rest of screen 'blank'
        for pos_x in range(x, self.width * self.cascaded):
            for pos_y in range(self.height):
                # print(x, y)
                self.point((pos_x, pos_y), self.backcolor)
                
        # center text
        if self.center_text:
            x = x-1
            # print("last_x_pos ", x)
            # print(self.width*self.cascaded - x)
            if self.width*self.cascaded - x > 1:
                # move everything
                ofset = int((self.width*self.cascaded - x)/2)
                for x in range(self.width*self.cascaded-1, -1, -1):
                    for y in range(self.height):
                        if x >= ofset:
                            color = list(self.strip[self.index_from_coordinates(x-ofset,y)])
                            color.append(self.intesity)
                            color = tuple(color)
                            self.strip[self.index_from_coordinates(x,y)] = color
                        else:
                            color = list(self.backcolor)
                            color.append(self.intesity)
                            color = tuple(color)
                            self.strip[self.index_from_coordinates(x,y)] = color

        self.draw()
