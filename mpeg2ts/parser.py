#!/usr/bin/env python3

from mpeg2ts.packet import Packet
from mpeg2ts.section import Section
from mpeg2ts.pes import PES

from collections import deque

class SectionParser:

  def __init__(self):
    self.section = None
    self.queue = deque()

  def push(self, packet):
    begin = Packet.HEADER_SIZE + (1 + packet.adaptation_field_length() if packet.has_adaptation_field() else 0)
    if packet.payload_unit_start_indicator(): begin += 1

    if not self.section:
      if packet.payload_unit_start_indicator():
        begin += packet.pointer_field()
      else:
        return

    if packet.payload_unit_start_indicator():
      while begin < Packet.PACKET_SIZE:
        if packet[begin] == Packet.STUFFING_BYTE[0]: break
        if self.section:
          next = min(begin + self.section.remains(), Packet.PACKET_SIZE)
        else:
          section_length = ((packet[begin + 1] & 0x0F) << 8) | packet[begin + 2]
          next = min(begin + (3 + section_length), Packet.PACKET_SIZE)
          self.section = Section()
        self.section += packet[begin:next]

        if self.section.fulfilled():
          self.queue.append(self.section)
          self.section = None

        begin = next
    else:
      next = min(begin + self.section.remains(), Packet.PACKET_SIZE)
      self.section += packet[begin:next]

      if self.section.fulfilled():
        self.queue.append(self.section)
        self.section = None

  def empty(self):
    return not self.queue

  def pop(self):
    return self.queue.popleft()

class PESParser:

  def __init__(self):
    self.pes = None
    self.queue = deque()

  def push(self, packet):
    begin = Packet.HEADER_SIZE + (1 + packet.adaptation_field_length() if packet.has_adaptation_field() else 0)
    if not packet.payload_unit_start_indicator() and not self.pes: return

    if packet.payload_unit_start_indicator():
      pes_length = (packet[begin + 3] << 16) | (packet[begin + 4] << 8) | packet[begin + 5]
      next = min(begin + (PES.HEADER_SIZE + pes_length), Packet.PACKET_SIZE)
      self.pes = PES(packet[begin:next])
    else:
      next = min(begin + self.pes.remains(), Packet.PACKET_SIZE)
      self.pes += packet[begin:next]

    if self.pes.fulfilled():
      self.queue.append(self.pes)
      self.pes = None

  def empty(self):
    return not self.queue

  def pop(self):
    return self.queue.popleft()
