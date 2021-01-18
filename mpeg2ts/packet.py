#!/usr/bin/env python3

class Packet:
  PACKET_SIZE = 188
  HEADER_SIZE = 4
  SYNC_BYTE = b'\x47'
  STUFFING_BYTE = b'\xff'

  def __init__(self, packet):
    self.packet = bytearray(packet)

  def __getitem__(self, item):
    return self.packet[item]

  def __setitem__(self, key, value):
    self.packet[key] = value

  def transport_error_indicator(self):
    return (self.packet[1] & 0x80) != 0

  def payload_unit_start_indicator(self):
    return (self.packet[1] & 0x40) != 0

  def transport_priority(self):
    return (self.packet[1] & 0x20) != 0

  def pid(self):
    return ((self.packet[1] & 0x1F) << 8) | self.packet[2]

  def has_adaptation_field(self):
    return (self.packet[3] & 0x20) != 0

  def has_payload(self):
    return (self.packet[3] & 0x10) != 0

  def continuity_counter(self):
    return self.packet[3] & 0x0F

  def adaptation_field_length(self):
    return self.packet[4] if self.has_adaptation_field() else 0

  def pointer_field(self):
    return self.packet[Packet.HEADER_SIZE + (1 + self.adaptation_field_length() if self.has_adaptation_field() else 0)]

  def has_pcr(self):
    return self.has_adaptation_field() and (self.packet[Packet.HEADER_SIZE + 1] & 0x10) != 0

  def pcr(self):
    if not self.has_pcr(): return None

    pcr_base = 0
    pcr_base = (pcr_base << 8) | ((self.packet[Packet.HEADER_SIZE + 1 + 1] & 0xFF) >> 0)
    pcr_base = (pcr_base << 8) | ((self.packet[Packet.HEADER_SIZE + 1 + 2] & 0xFF) >> 0)
    pcr_base = (pcr_base << 8) | ((self.packet[Packet.HEADER_SIZE + 1 + 3] & 0xFF) >> 0)
    pcr_base = (pcr_base << 8) | ((self.packet[Packet.HEADER_SIZE + 1 + 4] & 0xFF) >> 0)
    pcr_base = (pcr_base << 1) | ((self.packet[Packet.HEADER_SIZE + 1 + 5] & 0x10) >> 7)
    return pcr_base
