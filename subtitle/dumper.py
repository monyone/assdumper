from mpeg2ts.pes import PES

from subtitle.JIS8 import JIS8, CSI, ESC, G_SET, G_DRCS
from subtitle.color import pallets
from subtitle.dictionary import Dictionary, HIRAGANA, KATAKANA, ALNUM, KANJI, MACRO

class NotImplementedYetError(Exception):
  pass

class Dumper:

  def __init__(self, pes, accurate):
    self.pes = pes

    self.G_TEXT = {
      G_SET.KANJI: KANJI(),
      G_SET.ALNUM: ALNUM(),
      G_SET.HIRAGANA: HIRAGANA(),
      G_SET.KATAKANA: KATAKANA(),

      #エラーがでたら対応する
      G_SET.MOSAIC_A: None, # MOSAIC A
      G_SET.MOSAIC_B: None, # MOSAIC B
      G_SET.MOSAIC_C: None, # MOSAIC C
      G_SET.MOSAIC_D: None, # MOSAIC D
      # 実運用では出ないと規定されている
      G_SET.P_ALNUM: None, # P ALNUM (TODO: TR で使われないと規定されてるのでページ数を書く)
      G_SET.P_HIRAGANA: None, # P HIRAGANA (TODO: TR で使われないと規定されてるのでページ数を書く)
      G_SET.P_KATAKANA: None, # P KATAKANA (TODO: TR で使われないと規定されてるのでページ数を書く)
      # エラーが出たら対応する
      G_SET.JIS_X0201_KATAKANA: None, # JIS X0201 KATAKANA
      # ARIB TR-B14 第6.0版 第1分冊 p.89 で運用しないとされている
      G_SET.JIS_X0213_2004_KANJI_1: None, # JIS 1 KANJI
      G_SET.JIS_X0213_2004_KANJI_2: None, # JIS 2 KANJI
      G_SET.ADDITIONAL_SYMBOLS: None, # ADDITIONAL SYMBOLS
    }
    self.G_OTHER = {
      G_DRCS.DRCS_0: Dictionary(2, {}), # DRCS 2byte
      G_DRCS.DRCS_1: Dictionary(1, {}), # DRCS 1byte
      G_DRCS.DRCS_2: Dictionary(1, {}), # DRCS 1byte
      G_DRCS.DRCS_3: Dictionary(1, {}), # DRCS 1byte
      G_DRCS.DRCS_4: Dictionary(1, {}), # DRCS 1byte
      G_DRCS.DRCS_5: Dictionary(1, {}), # DRCS 1byte
      G_DRCS.DRCS_6: Dictionary(1, {}), # DRCS 1byte
      G_DRCS.DRCS_7: Dictionary(1, {}), # DRCS 1byte
      G_DRCS.DRCS_8: Dictionary(1, {}), # DRCS 1byte
      G_DRCS.DRCS_9: Dictionary(1, {}), # DRCS 1byte
      G_DRCS.DRCS_10: Dictionary(1, {}), # DRCS 1byte
      G_DRCS.DRCS_11: Dictionary(1, {}), # DRCS 1byte
      G_DRCS.DRCS_12: Dictionary(1, {}), # DRCS 1byte
      G_DRCS.DRCS_13: Dictionary(1, {}), # DRCS 1byte
      G_DRCS.DRCS_14: Dictionary(1, {}), # DRCS 1byte
      G_DRCS.DRCS_15: Dictionary(1, {}), # DRCS 1byte
      G_DRCS.MACRO: MACRO()
    }
    # (WARN: 本来は SWF は字幕管理データから取得する)
    self.swf, self.sdf, self.sdp = (960, 540), (960, 540), (0, 0)
    self.ssm, self.shs, self.svs = (36, 36), 4, 24
    self.text_size = (1, 1)
    self.use_pos = None # MEMO: SDF, SDF, SDP が変化している事があるため
    self.ass_pos = None # MEMO: SDF, SDF, SDP が変化している事があるため
    self.pallet = 0
    self.fg = pallets[self.pallet][7]
    self.orn = False
    self.stl = False
    self.hlc = False

    # ass 用
    self.lines = []
    self.accurate = accurate
    self.start_seconds = None
    self.current_seconds = None
    self.end_seconds = None
    self.appear_TIME = False

    self.initialize()

  def initialize(self):
    self.G_BACK = [
      self.G_TEXT[0x42],  # KANJI
      self.G_TEXT[0x4A],  # ALNUM
      self.G_TEXT[0x30],  # HIRAGANA
      self.G_OTHER[0x70], # MACRO
    ]
    self.GL = 0
    self.GR = 2

  def script_info(self):
    info = []
    info.append('[Script Info]')
    info.append('Title: Japanese Closed Caption Subtitlies')
    info.append('ScriptType: v4.00+')
    info.append('PlayResX: {}'.format(self.swf[0]))
    info.append('PlayResY: {}'.format(self.swf[1]))
    return '\n'.join(info) + '\n'

  def make_style(self, *, Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding):
    return 'Style: {},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}'.format(Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding)

  def styles(self):
    styles = []
    forground_color = '&H' + ''.join(['{:02X}'.format(val) for val in self.fg[:-1][::-1]]) #ffmpeg はアルファ未対応なので
    background_color = '&H' + ''.join(['{:02X}'.format(val) for val in self.bg[::-1]])

    styles.append('[V4+ Styles]')
    styles.append('Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding')
    styles.append(
      self.make_style(
        Name='nsz',
        Fontname='WadaLabChuMaruGo2004ARIB',
        Fontsize=36 - 8, # なぜかWadaLabChuMaruGo2004ARIBがデカく描写されるので
        PrimaryColour=forground_color, #固定
        SecondaryColour=forground_color, #固定
        OutlineColour=background_color,
        BackColour=background_color,
        Bold=0,
        Italic=0,
        Underline=0,
        StrikeOut=0,
        ScaleX=100,
        ScaleY=100,
        Spacing=0, #self.shs,
        Angle=0,
        BorderStyle=3,
        Outline=1,
        Shadow=0,
        Alignment=1,
        MarginL=0,
        MarginR=0,
        MarginV=0,
        Encoding=0
      )
    )
    styles.append(
      self.make_style(
        Name='msz',
        Fontname='WadaLabChuMaruGo2004ARIB',
        Fontsize=36 - 8, # なぜかWadaLabChuMaruGo2004ARIBがデカく描写されるので
        PrimaryColour=forground_color, #固定
        SecondaryColour=forground_color, #固定
        OutlineColour=background_color,
        BackColour=background_color,
        Bold=0,
        Italic=0,
        Underline=0,
        StrikeOut=0,
        ScaleX=100,
        ScaleY=100,
        Spacing=0, #self.shs // 2,
        Angle=0,
        BorderStyle=3,
        Outline=1,
        Shadow=0,
        Alignment=1,
        MarginL=0,
        MarginR=0,
        MarginV=0,
        Encoding=0
      )
    )
    styles.append(
      self.make_style(
        Name='ssz',
        Fontname='WadaLabChuMaruGo2004ARIB',
        Fontsize=18 - 4, # なぜかWadaLabChuMaruGo2004ARIBがデカく描写されるので
        PrimaryColour=forground_color, #固定
        SecondaryColour=forground_color, #固定
        OutlineColour=background_color,
        BackColour=background_color,
        Bold=0,
        Italic=0,
        Underline=0,
        StrikeOut=0,
        ScaleX=100,
        ScaleY=100,
        Spacing=0, #self.shs // 2,
        Angle=0,
        BorderStyle=3,
        Outline=1,
        Shadow=0,
        Alignment=1,
        MarginL=0,
        MarginR=0,
        MarginV=0,
        Encoding=0
      )
    )

    return '\n'.join(styles) + '\n'

  def events_info(self):
    events = []
    events.append('[Events]')
    events.append('Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text')
    return '\n'.join(events) + '\n'

  def body(self):
    body = []
    for line in self.lines:
      st_hour = (int(self.start_seconds) // 60) // 60
      st_min = (int(self.start_seconds) - (st_hour * 60 * 60)) // 60
      st_sec = (int(self.start_seconds) - (st_hour * 60 + st_min) * 60)
      st_msec = int((self.start_seconds - int(self.start_seconds)) * 100)

      ed_hour = ((int(self.end_seconds)) // 60) // 60
      ed_min = (int(self.end_seconds) - (ed_hour * 60 * 60)) // 60
      ed_sec = (int(self.end_seconds) - (ed_hour * 60 + ed_min) * 60)
      ed_msec = int((self.end_seconds - int(self.end_seconds)) * 100)

      starttime = '{:d}:{:02d}:{:02d}.{:02d}'.format(st_hour, st_min, st_sec, st_msec)
      endtime = '{:d}:{:02d}:{:02d}.{:02d}'.format(ed_hour, ed_min, ed_sec, ed_msec)
      body.append('Dialogue: 0,{},{},nsz,,0,0,0,,{}'.format(starttime, endtime, line))
    return '\n'.join(body) + '\n'

  def line_changed(self):
    self.lines.append('')
    self.text_format_changed()
    if self.accurate:
      self.lines[-1] += '{{\\pos({},{})}}'.format(self.use_pos[0], self.use_pos[1])
    else:
      self.lines[-1] += '{{\\pos({},{})}}'.format(self.ass_pos[0], self.ass_pos[1])

  def text_format_changed(self):
    if len(self.lines) == 0: return
    params = []

    if self.text_size == (1, 1):
      params.append('nsz')
    elif self.text_size == (0.5, 1):
      params.append('msz')
    elif self.text_size == (0.5, 0.5):
      params.append('ssz')
    else:
      raise NotImplementedYetError()

    #if self.hlc: params.append('hlc')
    #if self.stl: params.append('stl')
    #if self.orn: params.append('orn')

    self.lines[-1] += '{{\\r{}}}'.format('-'.join(params))
    self.forground_color_changed()

  def forground_color_changed(self):
    self.lines[-1] += '{{\\c&H{}&}}'.format(''.join(['{:02X}'.format(val) for val in self.fg[:-1][::-1]])) # ffmpeg はアルファ未対応なので

  def PES_header_data_length(self):
    return self.pes[PES.HEADER_SIZE + 2]

  def PTS(self):
    pts = 0
    pts <<= 3; pts |= ((self.pes[PES.HEADER_SIZE + 3 + 0] & 0x0E) >> 1)
    pts <<= 8; pts |= ((self.pes[PES.HEADER_SIZE + 3 + 1] & 0xFF) >> 0)
    pts <<= 7; pts |= ((self.pes[PES.HEADER_SIZE + 3 + 2] & 0xFE) >> 1)
    pts <<= 8; pts |= ((self.pes[PES.HEADER_SIZE + 3 + 3] & 0xFF) >> 0)
    pts <<= 7; pts |= ((self.pes[PES.HEADER_SIZE + 3 + 4] & 0xFE) >> 1)
    return pts

  def dump(self, elapsed_seconds):
    self.start_seconds = self.current_seconds = elapsed_seconds

    PES_data_packet_header_length = (self.pes[(PES.HEADER_SIZE + 3) + self.PES_header_data_length() + 2] & 0x0F)

    data_group = PES.HEADER_SIZE + (3 + self.PES_header_data_length()) + (3 + PES_data_packet_header_length)
    data_group_id = (self.pes[data_group + 0] & 0xFC) >> 2
    data_group_version = self.pes[data_group + 0] & 0x03
    data_group_number = self.pes[data_group + 1]
    last_data_group_number = self.pes[data_group + 2]
    data_group_size = (self.pes[data_group + 3] << 8) + self.pes[data_group + 4]
    CRC16 = (self.pes[data_group + (5 + data_group_size) + 0] << 8) | self.pes[data_group + (5 + data_group_size) + 1]

    if (data_group_id & 0x0F) != 1: # とりあえず第一言語字幕だけとる
      return False

    # TMD は字幕では 00 固定なので見ない (ARIB TR-B14 2 4.2.6 字幕文データの運用)

    data_unit = data_group + 9
    while data_unit < data_group + (5 + data_group_size):
      unit_separator = self.pes[data_unit + 0]
      data_unit_parameter = self.pes[data_unit + 1]
      data_unit_size = (self.pes[data_unit + 2] << 16) | (self.pes[data_unit + 3] << 8) | self.pes[data_unit + 4]

      if data_unit_parameter == 0x20:
        self.parse_text(data_unit + 5, data_unit + 5 + data_unit_size)
      elif data_unit_parameter == 0x35:
        raise NotImplementedYetError() # ビットマップデータ
      elif data_unit_parameter == 0x30:
        self.parse_DRCS(1, data_unit + 5, data_unit + 5 + data_unit_size)
      elif data_unit_parameter == 0x31:
        self.parse_DRCS(2, data_unit + 5, data_unit + 5 + data_unit_size)
      else:
        raise NotImplementedYetError() # 2バイトDRCS

      data_unit += 5 + data_unit_size
    return True

  def kukaku(self):
    width = int((self.shs + self.ssm[0]) * self.text_size[0])
    height = int((self.svs + self.ssm[1]) * self.text_size[1])
    return (width, height)
  def move_absolute_dot(self, x, y, changed = True):
    width, height = self.kukaku()
    new_pos = (x, y)
    print(new_pos)
    if self.use_pos:
      move = ((new_pos[0] - self.use_pos[0]) // width, (new_pos[1] - self.use_pos[1]) // height)
      move_mod = ((new_pos[0] - self.use_pos[0]) % width, (new_pos[1] - self.use_pos[1]) % height)
      if move_mod[0] == 0 and move_mod[1] == 0:
        self.move_relative_pos(move[0], move[1], False)
      elif move_mod[0] == 0:
        self.use_pos = (self.use_pos[0], new_pos[1])
        self.ass_pos = (self.ass_pos[0], new_pos[1])
        self.move_relative_pos(move[0], 0, False)
      elif move_mod[1] == 0:
        self.use_pos = (new_pos[0], self.use_pos[0])
        self.ass_pos = (new_pos[0], self.ass_pos[1])
        self.move_relative_pos(0, move[1], False)
      else:
        self.use_pos = self.ass_pos = new_pos
    else:
      self.use_pos = self.ass_pos = new_pos
    if changed: self.line_changed()
  def move_absolute_pos(self, x, y, changed = True):
    width, height = self.kukaku()
    new_pos = (self.sdp[0] + x * width, self.sdp[1] + (y + 1) * height)
    if self.use_pos:
      move = ((new_pos[0] - self.use_pos[0]) // width, (new_pos[1] - self.use_pos[1]) // height)
      move_mod = ((new_pos[0] - self.use_pos[0]) % width, (new_pos[1] - self.use_pos[1]) % height)
      if move_mod[0] == 0 and move_mod[1] == 0:
        self.move_relative_pos(move[0], move[1], False)
      elif move_mod[0] == 0:
        self.use_pos = (self.use_pos[0], new_pos[1])
        self.ass_pos = (self.ass_pos[0], new_pos[1])
        self.move_relative_pos(move[0], 0, False)
      elif move_mod[1] == 0:
        self.use_pos = (new_pos[0], self.use_pos[0])
        self.ass_pos = (new_pos[0], self.ass_pos[1])
        self.move_relative_pos(0, move[1], False)
      else:
        self.use_pos = self.ass_pos = new_pos
    else:
      self.use_pos = self.ass_pos = new_pos
    if changed: self.line_changed()
  def move_relative_pos(self, x, y, changed=True):
    if not self.use_pos:
      self.move_absolute_pos(0, 0, False)

    width, height = self.kukaku()
    while x < 0:
      x += 1
      self.use_pos = (self.use_pos[0] - width, self.use_pos[1])
      self.ass_pos = (self.ass_pos[0] - width, self.ass_pos[1])
      if self.use_pos[0] < self.sdp[0]:
        self.use_pos = (self.sdp[0] + self.sdf[0] - width, self.use_pos[1])
        self.ass_pos = (self.sdp[0] + self.sdf[0] - width, self.ass_pos[1])
        y -= 1
    while x > 0:
      x -= 1
      self.use_pos = (self.use_pos[0] + width, self.use_pos[1])
      self.ass_pos = (self.ass_pos[0] + width, self.ass_pos[1])
      if self.use_pos[0] >= self.sdp[0] + self.sdf[0]:
        self.use_pos = (self.sdp[0], self.use_pos[1])
        self.ass_pos = (self.sdp[0], self.ass_pos[1])
        y += 1
    if y < 0:
      if (height * abs(y)) > (self.ssm[1] + self.svs): # NSZ 1 区画を越えていたら
        while y < 0:
          y += 1
          self.use_pos = (self.use_pos[0], self.use_pos[1] - height)
          self.ass_pos = (self.ass_pos[0], self.ass_pos[1] - height)
      else:
        while y < 0:
          y += 1
          self.use_pos = (self.use_pos[0], self.use_pos[1] - height)
          self.ass_pos = (self.ass_pos[0], self.ass_pos[1] - height // 2)
      if changed: self.line_changed()
    if y > 0:
      if (height * abs(y)) > (self.ssm[1] + self.svs): # NSZ 1 区画を越えていたら
        while y > 0:
          y -= 1
          self.use_pos = (self.use_pos[0], self.use_pos[1] + height)
          self.ass_pos = (self.ass_pos[0], self.ass_pos[1] + height)
      else:
        while y > 0:
          y -= 1
          self.use_pos = (self.use_pos[0], self.use_pos[1] + height)
          self.ass_pos = (self.ass_pos[0], self.ass_pos[1] + height // 2)
      if changed: self.line_changed()

  def move_newline(self):
    if not self.use_pos:
      self.move_absolute_pos(0, 0, False)

    width, height = self.kukaku()
    self.use_pos = (self.sdp[0], self.use_pos[1] + height)
    self.ass_pos = (self.sdp[0], self.ass_pos[1] + height // 2)

    self.line_changed()

  def parse_DRCS(self, size, begin, end):
    NumberOfCode = self.pes[begin + 0]
    begin += 1
    while begin < end:
      CharacterCode = (self.pes[begin + 0] << 8) | self.pes[begin + 1]
      NumberOfFont = self.pes[begin + 2]
      if size == 1:
        # 0x41 - 0x4F までが 1byte DRCS の対応なので、下の 4bit だけ取る
        index, ch = (CharacterCode & 0x0F00) >> 8, (CharacterCode & 0x00FF) >> 0
      elif size == 2:
        ch1, ch2 = (CharacterCode & 0xFF00) >> 8, (CharacterCode & 0x00FF) >> 0

      begin += 3
      for font in range(NumberOfFont):
        fontId = (self.pes[begin + 0] & 0xF0) >> 4
        mode = self.pes[begin + 0] & 0x0F
        if mode == 0b0000 or mode == 0b0001 : #無圧縮の1bit(0000) or Nbit(0001) の DRCS
          depth = self.pes[begin + 1]
          width = self.pes[begin + 2]
          height = self.pes[begin + 3]
          depth_bits = len(bin(depth + 2)) - len(bin(depth + 2).rstrip('0'))
          length = (width * height * depth_bits) // 8 # FIXME: depth = 階調数 - 2 なので対応する
          if size == 1:
            self.G_OTHER[0x40 + index][ch] = self.pes[begin + 4: begin + 4 + length]
            begin += 4 + length
          elif size == 2:
            self.G_OTHER[0x40][(ch1, ch2)] = self.pes[begin + 4: begin + 4 + length]
            begin += 4 + length
          else:
            raise NotImplementedYetError()
        else: # ジオメトリック図形は運用しない(TR-B14にて)
          raise NotImplementedYetError()

  def parse_text(self, begin, end):
    while begin < end:
      byte = self.pes[begin]
      if 0x20 < byte and byte < 0x7F:
        size = self.G_BACK[self.GL].size
        self.render_character(self.pes[begin:begin+size], self.G_BACK[self.GL])
        begin += size
      elif 0xA0 < byte and byte < 0xFF:
        size = self.G_BACK[self.GR].size
        self.render_character(self.pes[begin:begin+size], self.G_BACK[self.GR])
        begin += size
      elif byte == JIS8.NUL:
        begin += 1 # (TODO: ignore したことをログに残す)
      elif byte == JIS8.BEL:
        begin += 1 # (TODO: ignore したことをログに残す)
      elif byte == JIS8.APB:
        self.move_relative_pos(-1, 0)
        begin += 1
      elif byte == JIS8.APF:
        self.move_relative_pos(1, 0)
        begin += 1
      elif byte == JIS8.APD:
        self.move_relative_pos(0, 1)
        begin += 1
      elif byte == JIS8.APU:
        self.move_relative_pos(0, -1)
        begin += 1
      elif byte == JIS8.CS:
        if self.appear_TIME:
          self.end_seconds = self.current_seconds
        begin += 1 # (TODO: ignore したことをログに残す)
      elif byte == JIS8.APR:
        self.move_newline()
        begin += 1
      elif byte == JIS8.LS1:
        self.GL = 1
        begin += 1
      elif byte == JIS8.LS0:
        self.GL = 0
        begin += 1
      elif byte == JIS8.PAPF:
        P1 = self.pes[begin + 1] & 0x3F # x
        self.move_relative_pos(P1, 0)
        begin += 2
      elif byte == JIS8.CAN:
        begin += 1 # (TODO: ignore したことをログに残す)
      elif byte == JIS8.SS2:
        size = self.G_BACK[2].size
        self.render_character(self.pes[begin + 1: begin + 1 + size], self.G_BACK[2])
        begin += 1 + size
      elif byte == JIS8.ESC:
        if self.pes[begin + 1] == ESC.LS2: ## LS2
          self.GL = 2 #GL = G2
          begin += 2
        elif self.pes[begin + 1] == ESC.LS3: ## LS3
          self.GL = 3 #GL = G3
          begin += 2
        elif self.pes[begin + 1] == ESC.LS1R: ## LS1R
          self.GR = 1 #GR = G1
          begin += 2
        elif self.pes[begin + 1] == ESC.LS2R: ## LS2R
          self.GR = 2 #GR = G2
          begin += 2
        elif self.pes[begin + 1] == ESC.LS3R: ## LS3R
          self.GR = 3 #GR = G3
          begin += 2
        elif self.pes[begin + 1] == 0x28: # G0 (1 byte)
          if self.pes[begin + 2] == 0x20: # DRCS
            self.G_BACK[0] = self.G_OTHER[self.pes[begin + 3]]
            begin += 4
          else:
            self.G_BACK[0] = self.G_TEXT[self.pes[begin + 2]]
            begin += 3
        elif self.pes[begin + 1] == 0x29: # G1 (1 byte)
          if self.pes[begin + 2] == 0x20: # DRCS
            self.G_BACK[1] = self.G_OTHER[self.pes[begin + 3]]
            begin += 4
          else:
            self.G_BACK[1] = self.G_TEXT[self.pes[begin + 2]]
            begin += 3
        elif self.pes[begin + 1] == 0x2A: # G2 (1 byte)
          if self.pes[begin + 2] == 0x20: # DRCS
            self.G_BACK[2] = self.G_OTHER[self.pes[begin + 3]]
            begin += 4
          else:
            self.G_BACK[2] = self.G_TEXT[self.pes[begin + 2]]
            begin += 3
        elif self.pes[begin + 1] == 0x2B: # G3 (1 byte)
          if self.pes[begin + 2] == 0x20: # DRCS
            self.G_BACK[3] = self.G_OTHER[self.pes[begin + 3]]
            begin += 4
          else:
            self.G_BACK[3] = self.G_TEXT[self.pes[begin + 2]]
            begin += 3
        elif self.pes[begin + 1] == 0x24: # 2 byte
          if self.pes[begin + 2] == 0x28: # G0 (2 byte)
            if self.pes[begin + 3] == 0x20: # DRCS
              self.G_BACK[0] = self.G_OTHER[self.pes[begin + 4]]
              begin += 5
            else:
              self.G_BACK[0] = self.G_TEXT[self.pes[begin + 3]]
              begin += 4
          if self.pes[begin + 2] == 0x29: # G1 (2 byte)
            if self.pes[begin + 3] == 0x20: # DRCS
              self.G_BACK[0] = self.G_OTHER[self.pes[begin + 4]]
              begin += 5
            else:
              self.G_BACK[0] = self.G_TEXT[self.pes[begin + 3]]
              begin += 4
          if self.pes[begin + 2] == 0x2A: # G2 (2 byte)
            if self.pes[begin + 3] == 0x20: # DRCS
              self.G_BACK[0] = self.G_OTHER[self.pes[begin + 4]]
              begin += 5
            else:
              self.G_BACK[0] = self.G_TEXT[self.pes[begin + 3]]
              begin += 4
          if self.pes[begin + 2] == 0x2B: # G3 (2 byte)
            if self.pes[begin + 3] == 0x20: # DRCS
              self.G_BACK[0] = self.G_OTHER[self.pes[begin + 4]]
              begin += 5
            else:
              self.G_BACK[0] = self.G_TEXT[self.pes[begin + 3]]
              begin += 4
        else:
          raise NotImplementedYetError(JIS8.ESC)
      elif byte == JIS8.APS:
        P1 = self.pes[begin + 1] & 0x3F # y
        P2 = self.pes[begin + 2] & 0x3F # x
        self.move_absolute_pos(P2, P1)
        begin += 3
      elif byte == JIS8.SS3:
        size = self.G_BACK[3].size
        self.render_character(self.pes[begin + 1: begin + 1 + size], self.G_BACK[3])
        begin += 1 + size
      elif byte == JIS8.RS:
        begin += 1 # (TODO: ignore したことをログに残す)
      elif byte == JIS8.US:
        begin += 1 # (TODO: ignore したことをログに残す)
      elif byte == JIS8.SP:
        self.render_character(b'\xa1\xa1', self.G_TEXT[G_SET.KANJI]) # 全角スペース
        begin += 1
      elif byte == JIS8.DEL:
        begin += 1 # (TODO: ignore したことをログに残す)
      elif byte == JIS8.BKF:
        self.fg = pallets[self.pallet][0]
        self.forground_color_changed()
        begin += 1
      elif byte == JIS8.RDF:
        self.fg = pallets[self.pallet][1]
        self.forground_color_changed()
        begin += 1
      elif byte == JIS8.GRF:
        self.fg = pallets[self.pallet][2]
        self.forground_color_changed()
        begin += 1
      elif byte == JIS8.YLF:
        self.fg = pallets[self.pallet][3]
        self.forground_color_changed()
        begin += 1
      elif byte == JIS8.BLF:
        self.fg = pallets[self.pallet][4]
        self.forground_color_changed()
        begin += 1
      elif byte == JIS8.MGF:
        self.fg = pallets[self.pallet][5]
        self.forground_color_changed()
        begin += 1
      elif byte == JIS8.CNF:
        self.fg = pallets[self.pallet][6]
        self.forground_color_changed()
        begin += 1
      elif byte == JIS8.WHF:
        self.fg = pallets[self.pallet][7]
        self.forground_color_changed()
        begin += 1
      elif byte == JIS8.SSZ:
        self.text_size = (0.5, 0.5)
        self.text_format_changed()
        begin += 1
      elif byte == JIS8.MSZ:
        self.text_size = (0.5, 1)
        self.text_format_changed()
        begin += 1
      elif byte == JIS8.NSZ:
        self.text_size = (1, 1)
        self.text_format_changed()
        begin += 1
      elif byte == JIS8.SZX:
        raise NotImplementedYetError(JIS8.SZX)
      elif byte == JIS8.COL:
        P1 = self.pes[begin + 1]
        if P1 == 0x20:
          P2 = self.pes[begin + 2] & 0x0F
          self.pallet = P2
          begin += 3
        else:
          color = P1 & 0x0F
          if (P1 & 0x70) == 0x40:
            self.fg = pallets[self.pallet][color]
            self.forground_color_changed()
          elif (P1 & 0x70) == 0x50:
            self.bg = pallets[self.pallet][color]
            pass
          else:
            # (TODO: ignore したことをログに残す)
            pass
          begin += 2
      elif byte == JIS8.FLC: # 点滅(電話の着信を表す字幕で使われる)
        begin += 2 # (TODO: ignore したことをログに残す)
      elif byte == JIS8.CDC:
        raise NotImplementedYetError(JIS8.CDC)
      elif byte == JIS8.POL:
        raise NotImplementedYetError(JIS8.POL)
      elif byte == JIS8.WMM:
        raise NotImplementedYetError(JIS8.WMM)
      elif byte == JIS8.MACRO:
        raise NotImplementedYetError(JIS8.MACRO)
      elif byte == JIS8.HLC:
        if (self.pes[begin + 1] & 0x0F) != 0:
          if not self.hlc:
            self.hlc = True
            self.text_format_changed()
        else:
          if self.hlc:
            self.hlc = False
            self.text_format_changed()
        begin += 2
      elif byte == JIS8.RPC:
        raise NotImplementedYetError(JIS8.RPC)
      elif byte == JIS8.SPL:
        self.stl = False
        self.text_format_changed()
        begin += 1
      elif byte == JIS8.STL:
        self.stl = True
        self.text_format_changed()
        begin += 1
      elif byte == JIS8.CSI:
        last = begin + 1
        while True:
          if self.pes[last] == CSI.GSM:
            raise NotImplementedYetError(CSI.GSM)
          elif self.pes[last] == CSI.SWF:
            index = begin + 1
            P1 = 0
            while self.pes[index] != 0x3B and self.pes[index] != 0x20:
              P1 *= 10
              P1 += self.pes[index] & 0x0F
              index += 1
            if self.pes[index] != 0x20:
              raise NotImplementedYetError(CSI.SWF)
            elif P1 == 5:
              self.swf = (1920, 1080)
            elif P1 == 7:
              self.swf = (960, 540)
            elif P1 == 9:
              self.swf = (720, 480)
            else:
              raise NotImplementedYetError(CSI.SWF)
            break
          elif self.pes[last] == CSI.CCC:
            raise NotImplementedYetError(CSI.CCC)
          elif self.pes[last] == CSI.SDF:
            index = begin + 1
            P1, P2 = 0, 0
            while self.pes[index] != 0x3B:
              P1 *= 10
              P1 += self.pes[index] & 0x0F
              index += 1
            index += 1
            while self.pes[index] != 0x20:
              P2 *= 10
              P2 += self.pes[index] & 0x0F
              index += 1
            self.sdf = (P1, P2)
            break
          elif self.pes[last] == CSI.SSM:
            index = begin + 1
            P1, P2 = 0, 0
            while self.pes[index] != 0x3B:
              P1 *= 10
              P1 += self.pes[index] & 0x0F
              index += 1
            index += 1
            while self.pes[index] != 0x20:
              P2 *= 10
              P2 += self.pes[index] & 0x0F
              index += 1
            self.ssm = (P1, P2)
            break
          elif self.pes[last] == CSI.SHS:
            index = begin + 1
            P1 = 0
            while self.pes[index] != 0x20:
              P1 *= 10
              P1 += self.pes[index] & 0x0F
              index += 1
            self.shs = P1
            break
          elif self.pes[last] == CSI.SVS:
            index = begin + 1
            P1 = 0
            while self.pes[index] != 0x20:
              P1 *= 10
              P1 += self.pes[index] & 0x0F
              index += 1
            self.svs = P1
            break
          elif self.pes[last] == CSI.PLD:
            raise NotImplementedYetError(CSI.PLD)
          elif self.pes[last] == CSI.PLU:
            raise NotImplementedYetError(CSI.PLU)
          elif self.pes[last] == CSI.GAA:
            raise NotImplementedYetError(CSI.GAA)
          elif self.pes[last] == CSI.SRC:
            raise NotImplementedYetError(CSI.SRC)
          elif self.pes[last] == CSI.SDP:
            index = begin + 1
            P1, P2 = 0, 0
            while self.pes[index] != 0x3B:
              P1 *= 10
              P1 += self.pes[index] & 0x0F
              index += 1
            index += 1
            while self.pes[index] != 0x20:
              P2 *= 10
              P2 += self.pes[index] & 0x0F
              index += 1
            self.sdp = (P1, P2)
            break
          elif self.pes[last] == CSI.ACPS:
            index = begin + 1
            P1, P2 = 0, 0
            while self.pes[index] != 0x3B:
              P1 *= 10
              P1 += self.pes[index] & 0x0F
              index += 1
            index += 1
            while self.pes[index] != 0x20:
              P2 *= 10
              P2 += self.pes[index] & 0x0F
              index += 1
            self.move_absolute_dot(P1, P2)
            break
          elif self.pes[last] == CSI.TCC:
            raise NotImplementedYetError(CSI.TCC)
          elif self.pes[last] == CSI.ORN:
            P1 = self.pes[begin + 1]
            if P1 == 0x30:
              if self.orn:
                self.orn = None
                self.text_format_changed()
            elif P1 == 0x31:
              P2 = (self.pes[begin + 3] & 0x0F) + (self.pes[begin + 4] & 0x0F)
              P3 = (self.pes[begin + 5] & 0x0F) + (self.pes[begin + 6] & 0x0F)
              if not self.orn:
                self.orn = pallets[P2][P3]
                self.text_format_changed()
            else:
              raise NotImplementedYetError(CSI.ORN)
            break
          elif self.pes[last] == CSI.MDF:
            raise NotImplementedYetError(CSI.MDF)
          elif self.pes[last] == CSI.CFS:
            raise NotImplementedYetError(CSI.CFS)
          elif self.pes[last] == CSI.XCS:
            raise NotImplementedYetError(CSI.XCS)
          elif self.pes[last] == CSI.SCR:
            raise NotImplementedYetError(CSI.SCR)
          elif self.pes[last] == CSI.PRA:
            raise NotImplementedYetError(CSI.PRA)
          elif self.pes[last] == CSI.ACS:
            raise NotImplementedYetError(CSI.ACS)
          elif self.pes[last] == CSI.UED:
            raise NotImplementedYetError(CSI.UED)
          elif self.pes[last] == CSI.RCS: # (CS の代わりに塗りつぶしで場合がある)
            break #(TODO: 無視した事をログする)
          elif self.pes[last] == CSI.SCS:
            raise NotImplementedYetError(CSI.SCS)
          else:
            last += 1
        begin = last + 1
      elif byte == JIS8.TIME:
        if self.pes[begin + 1] == 0x20:
          P2 = self.pes[begin + 2] & 0x3F
          self.appear_TIME = True
          self.current_seconds += P2 / 10
          begin += 3
        elif self.pes[begin + 1] == 0x28:
          raise NotImplementedYetError(JIS8.TIME)
        else:
          raise NotImplementedYetError(JIS8.TIME)
      else:
        raise NotImplementedYetError(hex(byte))

  def render_character(self, ch_byte, dict):
    if not self.use_pos: self.move_absolute_pos(0, 0)
    width, height = self.kukaku()

    character_key = int.from_bytes(ch_byte, byteorder='big') & int.from_bytes(b'\x7F' * dict.size, byteorder='big')
    character = dict[character_key]

    if type(character) == tuple: # MACRO
      self.G_BACK = [(self.G_TEXT[dictionary] if dictionary in G_SET else self.G_OTHER[dictionary]) for dictionary in character]
      self.GL = 0
      self.GR = 2
      return
    elif type(character) == bytearray: # DRCS
      drcs = (int(self.ssm[0] * self.text_size[0]) // 2, int(self.ssm[1] * self.text_size[1]) // 2)
      depth = len(character) * 8 // (drcs[0] * drcs[1])
      for y in range(drcs[1]):
        for x in range(drcs[0]):
          value = 0
          for d in range(depth):
            byte = (((y * drcs[0] + x) * depth) + d) // 8
            index = 7 - ((((y * drcs[0] + x) * depth) + d) % 8)
            value *= 2
            value += (character[byte] & (1 << index)) >> index
          if value != 0:
            pass
    else:
      self.lines[-1] += character

    self.move_relative_pos(1, 0)
