def BCD(byte):
  return (((byte & 0xF0) >> 4) * 10) + (byte & 0x0F)

def MJD_to_YMD(MJD):
  MJD += 678881
  a = 4 * MJD + 3 + 4 * ((3 * (((4 * (MJD + 1)) // 146097 + 1))) // 4)
  b = 5 * ((a % 1461) // 4) + 2
  Y, M, D = a // 1461, b // 153, (b % 153) // 5
  day = D + 1
  month = (M + 3 - 12) if (M + 3) > 12 else (M + 3)
  year = Y + 1 if M + 3 > 12 else Y
  return year, month, day

def YMD_to_MJD(Y, M, D):
  y = Y + (M - 3) // 12
  m = (M - 3) % 12
  d = D - 1
  n = d + (153 * m + 2) // 5 + (365 * y) + (y // 4) - (y // 100) + (y // 400)
  return n - 678881
