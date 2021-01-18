#!/usr/bin/env python3

import argparse
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

from PIL import Image

from mpeg2ts.packet import Packet
from mpeg2ts.section import Section
from mpeg2ts.parser import SectionParser, PESParser
from mpeg2ts.mjd import BCD, MJD_to_YMD
from subtitle.dumper import Dumper

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description=('ARIB subtitle renderer'))

  parser.add_argument('-i', '--input', type=argparse.FileType('rb'), nargs='?', default=sys.stdin.buffer)
  parser.add_argument('-o', '--output', type=argparse.FileType('w'), nargs='?', default=sys.stdout)
  parser.add_argument('-s', '--SID', type=int, required=True)

  args = parser.parse_args()

  PAT_Parser = SectionParser()
  PMT_Parser = SectionParser()
  SUBTITLE_Parser = PESParser()

  PMT_PID = -1
  PCR_PID = -1
  SUBTITLE_PID = -1

  FIRST_PCR = None

  prev_dumper = None
  ALREADY_OUTPUT_HEADER = False

  while args.input:
    while True:
      sync_byte = args.input.read(1)
      if not sync_byte: sys.exit()
      if sync_byte == Packet.SYNC_BYTE: break

    packet = Packet.SYNC_BYTE + args.input.read(Packet.PACKET_SIZE - 1)
    ts = Packet(packet)

    if ts.pid() == 0x00:
      PAT_Parser.push(ts)
      while not PAT_Parser.empty():
        PAT = PAT_Parser.pop()
        if PAT.CRC32() != 0: continue

        begin = Section.HEADER_SIZE
        while begin < 3 + PAT.section_length() - Section.CRC_SIZE:
          program_number = (PAT[begin + 0] << 8) | PAT[begin + 1]
          program_map_PID = ((PAT[begin + 2] & 0x1F) << 8) | PAT[begin + 3]

          if program_number == args.SID:
            PMT_PID = program_map_PID

          begin += 4
    elif ts.pid() == PMT_PID:
      PMT_Parser.push(ts)
      while not PMT_Parser.empty():
        PMT = PMT_Parser.pop()
        if PMT.CRC32() != 0: continue

        PCR_PID = ((PMT[Section.HEADER_SIZE + 0] & 0x1F) << 8) | PMT[Section.HEADER_SIZE + 1]
        program_info_length = ((PMT[Section.HEADER_SIZE + 2] & 0x0F) << 8) | PMT[Section.HEADER_SIZE + 3]

        begin = Section.HEADER_SIZE + 4 + program_info_length
        while begin < 3 + PMT.section_length() - Section.CRC_SIZE:
          stream_type = PMT[begin + 0]
          elementary_PID = ((PMT[begin + 1] & 0x1F) << 8) | PMT[begin + 2]
          ES_info_length = ((PMT[begin + 3] & 0x0F) << 8) | PMT[begin + 4]

          descriptor = begin + 5
          while descriptor < (begin + 5 + ES_info_length):
            descriptor_tag = PMT[descriptor + 0]
            descriptor_length = PMT[descriptor + 1]
            if descriptor_tag == 0x52:
              component_tag = PMT[descriptor + 2]
              if stream_type == 0x06 and component_tag == 0x30: # Aプロファイルの字幕のデフォルトESが 0x30  (ARIB TR-B14 2 4.2.8.1 コンポーネントタグの運用)
                SUBTITLE_PID = elementary_PID
            descriptor += 2 + descriptor_length

          begin += 5 + ES_info_length
    elif ts.pid() == PCR_PID:
      if not FIRST_PCR:
        FIRST_PCR = ts.pcr()
    elif ts.pid() == SUBTITLE_PID:
      SUBTITLE_Parser.push(ts)
      while not SUBTITLE_Parser.empty():
        SUBTITLE = SUBTITLE_Parser.pop()
        if not FIRST_PCR: continue

        dumper = Dumper(SUBTITLE)
        elapsed_seconds = seconds = (((1 << 33) - 1) + (dumper.PTS() - FIRST_PCR)) % ((1 << 33) - 1) / 90000

        if not dumper.dump(elapsed_seconds): continue

        if prev_dumper:
          prev_dumper.end_seconds = elapsed_seconds
          if len(prev_dumper.lines) > 0:
            if not ALREADY_OUTPUT_HEADER:
              args.output.write(prev_dumper.script_info())
              args.output.write('\n')
              args.output.write(prev_dumper.styles())
              args.output.write('\n')
              args.output.write(prev_dumper.events_info())
              ALREADY_OUTPUT_HEADER = True

            args.output.write(prev_dumper.body())

        if dumper.end_seconds is not None:
          if len(dumper.lines) > 0:
            if not ALREADY_OUTPUT_HEADER:
              args.output.write(dumper.script_info())
              args.output.write('\n')
              args.output.write(dumper.styles())
              args.output.write('\n')
              args.output.write(dumper.events_info())
              ALREADY_OUTPUT_HEADER = True

            args.output.write(dumper.body())
          prev_dumper = None
        else:
          prev_dumper = dumper
