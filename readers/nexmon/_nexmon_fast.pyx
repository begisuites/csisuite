# distutils: extra_compile_args=-O3

from typing import Dict
import numpy as np
import io
import struct
from datetime import datetime, timedelta
import socket
import time
from pathlib import Path

cimport numpy as cnp
from cpython.bytes cimport PyBytes_AS_STRING

ctypedef cnp.int16_t  i16
ctypedef cnp.float32_t f32
ctypedef cnp.complex64_t c64

CHIPS_INT = {
    0x0001: "4339",
    0x0065: "43455c0",
    0xa6dc: "43455c0",
    0x0003: "4358",
    0xdead: "4358",
    0xe834: "4366c0",
    0x006a: "4366c0",
}

S_PCAP_HEAD   = struct.Struct('<IHHIIII')        # (24) magic_number, version_major, version_minor, thiszone, sigfigs, snaplen, network
S_PCAP_PKT    = struct.Struct('=IIII')           # (16) ts_sec, ts_usec, incl_len, orig_len
S_ETH         = struct.Struct('!6s6sH')          # (14) Ethernet
S_IP_MIN      = struct.Struct('!BBHHHBBH4s4s')   # (20) Minimal IPv4
S_UDP         = struct.Struct('!HHHH')           # (8) UDP
S_CHAR_SIGNED = struct.Struct('b')               # (2) signed char
S_CHAR        = struct.Struct('B')               # (2) unsigned char

MAC_CACHE : Dict[bytes, str] = {}               # MACs cache for faster formatting

def format_mac(mac_bytes: bytes) -> str:
    if mac_bytes in MAC_CACHE:
        return MAC_CACHE[mac_bytes]
    
    h = mac_bytes.hex()
    mac_str = ':'.join(h[i:i+2] for i in range(0, 12, 2))
    MAC_CACHE[mac_bytes] = mac_str
    return mac_str

def read_exact(input, length) -> bytes:
    bytes = input.read(length)
    if len(bytes) != length:
        raise EOFError(f'Reached end of file before reading the expected number of bytes: {bytes.hex()}')
    return bytes

def read_pcap_global_header(input, verbose=False):
    pcap_global_header = read_exact(input, S_PCAP_HEAD.size)
    if verbose:
        magic_number, version_major, version_minor, thiszone, sigfigs, snaplen, network = S_PCAP_PKT.unpack(pcap_global_header)
        print(f'Global header ({len(pcap_global_header)} bytes)', pcap_global_header.hex())
        print('  Magic Number:   ', hex(magic_number))
        print('  Version:        ', f'{version_major}.{version_minor}')
        print('  Thiszone:       ', thiszone)
        print('  Sigfigs:        ', sigfigs)
        print('  Snaplen:        ', snaplen)
        print('  Network:        ', network)
        if network == 1:
            print('  Network Type:   ', 'Ethernet (DIX)')
        elif network == 228:
            print('  Network Type:   ', 'IEEE 802.11 wireless LAN')
        else:
            print('  Network Type:   ', f'Unknown ({network})')
    return pcap_global_header

def read_pcap_packet_header(input, verbose=False):
    pcap_packet_header = read_exact(input, S_PCAP_PKT.size)
    ts_sec, ts_usec, incl_len, orig_len = S_PCAP_PKT.unpack(pcap_packet_header)
    #timestamp = datetime.fromtimestamp(ts_sec + ts_usec / 1_000_000)
    timestamp = ts_sec + ts_usec * 1e-6 
    if verbose:
        print(f'\nPacket header ({len(pcap_packet_header)} bytes)', pcap_packet_header.hex())
        print('  Timestamp:', timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
        print('  Included Length:', incl_len)
        print('  Original Length:', orig_len)
    return timestamp, incl_len

def read_ethernet_header(input, verbose=False):
    eth_header = read_exact(input, S_ETH.size)
    dst_mac, src_mac, eth_type = S_ETH.unpack(eth_header)
    if verbose:
        print(f'\nEthernet header ({len(eth_header)} bytes)', eth_header.hex())
        print("  Destination MAC:", format_mac(dst_mac))
        print("  Source MAC:     ", format_mac(src_mac))
        print("  Ethertype:      ", 'IPv4' if eth_type == 0x0800 else f'0x{eth_type:04x}')
    return dst_mac, src_mac, eth_type

def read_ip_header(input, verbose=False):
    ip_header = read_exact(input, S_IP_MIN.size)
    ip_fields = S_IP_MIN.unpack(ip_header)
    ip_src, ip_dst = socket.inet_ntoa(ip_fields[8]), socket.inet_ntoa(ip_fields[9])
    if verbose:
        print(f'\nIP header ({len(ip_header)} bytes)', ip_header.hex())
        print("  Version:        ", ip_fields[0] >> 4)
        print("  Header Length:  ", ip_fields[0] & 0x0F)
        print("  Total Length:   ", ip_fields[2])
        print("  Protocol:       ", ip_fields[6])
        print("  Source IP:      ", ip_src)
        print("  Destination IP: ", ip_dst)
    return ip_src, ip_dst

def read_udp_header(input, verbose=False):
    udp_header = read_exact(input, S_UDP.size)
    src_port, dst_port, length, checksum = S_UDP.unpack(udp_header)
    if verbose:
        print(f"\nUDP ({len(udp_header)} bytes):")
        print("  Source Port:     ", src_port)
        print("  Destination Port:", dst_port)
        print("  Length:          ", length)
        print("  Checksum:        ", checksum)
    return src_port, dst_port, length, checksum

def parse_csi_to_c64(bytes data, int num_subcarriers):
    cdef Py_ssize_t i

    # Get a raw pointer to the bytes buffer and point at int16 IQ starting at offset 18
    cdef const unsigned char* base = <const unsigned char*> PyBytes_AS_STRING(data)
    cdef const i16* p = <const i16*>(base + 18)

    cdef cnp.ndarray[c64, ndim=1] out = np.empty(num_subcarriers, dtype=np.complex64)
    cdef c64* o = <c64*> out.data

    for i in range(num_subcarriers):
        o[i].real = <f32> p[2*i]
        o[i].imag = <f32> p[2*i + 1]

    return out

def read_nexmon_csi(input, length, verbose=False):
    data = read_exact(input, length)
    nexmon_signature = data[:2]
    rssi = data[2] if data[2] < 128 else data[2] - 256          # signed char
    frame_control = data[3]                                     # unsigned char
    mac = format_mac(data[4:10])                                # string
    sequence_no = data[10] | (data[11] << 8)                    # unsigned int little endian
    coreSpatialVal = data[12] | (data[13] << 8)                 # unsigned int little endian
    channel_spec = data[14:16]                                  # int
    chip = CHIPS_INT[data[16] | (data[17] << 8)]                # unsigned int little endian
    num_subcarriers = (len(data) - 18) // 4
    
    if chip in ["4339", "43455c0"]:
        csi = parse_csi_to_c64(data, num_subcarriers)
        return csi, mac
        # return csi_float32.view(np.complex64), mac
    elif chip == "4366c0":
        csi = np.frombuffer(data[18:], dtype=np.uint32)  # Convert bytes → float16 array
        csi = unpack_float_acphy(10, 1, 12, 6, num_subcarriers, csi)
        csi = csi.astype(np.float32).view(np.complex64)     # Truco para convertir a complejos sin loops
    else:
        raise Exception(f'Unsupported chip: "{chip}"')
    
    if verbose:
        print(f'\nNexmon CSI Packet ({len(data)} bytes)', data.hex())
        print('  Signature:          ', nexmon_signature)
        print('  RSSI:               ', rssi)
        print('  Frame Control:      ', frame_control)
        print('  MAC:                ', mac)
        print('  Sequence No:        ', sequence_no)
        print('  Core Spatial Stream:', coreSpatialVal)
        print('  Channel Spec:       ', channel_spec)
        print('  Chip:               ', chip)
        print('  Number of Subcarriers:', num_subcarriers)
        print('  CSI Data:            ', len(data[18:]), 'bytes', len(csi), 'complex values')

    return csi, mac

def unpack_float_acphy(
        nbits: int, autoscale: bool,
        nman: int, nexp: int, nfft: int, H: np.ndarray
) -> np.ndarray:
    """
    Vectorised clone of `unpack_float_acphy` (bit-exact).
    H  : 1-D uint32 / uint64 NumPy array, length == nfft
    out: int64 array, length == 2*nfft
    """

    H = H.astype(np.uint64, copy=False)

    # --- constant masks ----------------------------------------------------
    iq_mask  = (1 << (nman - 1)) - 1
    e_mask   = (1 << nexp) - 1
    e_p      = 1 << (nexp - 1)
    sign_bit = 1 << 31

    sgnr_mask = 1 << (nexp + 2 * nman - 1)
    sgni_mask = sgnr_mask >> nman
    e_zero    = -nman

    # --- de-interleave mantissas & raw exponents ---------------------------
    vi = ((H >> (nexp + nman)) & iq_mask).astype(np.int64)
    vq = ((H >> nexp)          & iq_mask).astype(np.int64)

    e  = (H & e_mask).astype(np.int64)
    e[e >= e_p] -= (e_p << 1)                       # sign-extend exponent
    e_orig = e.copy()                               # keep the *un-scaled* copy

    # --- autoscale: find how far we *could* shift each mantissa ------------
    if autoscale:
        x = vi | vq
        x[x==0] = 1 # Evitar log(0)
        extra = np.where(x, np.floor(np.log2(x)).astype(np.int64), 0)
        maxbit = (e + extra).max(initial=-e_p)      # only for normalisation
    else:
        maxbit = e.max(initial=-e_p)

    shift = nbits - maxbit                          # same global offset

    # --- attach explicit sign bits -----------------------------------------
    vi[H & sgnr_mask != 0] |= sign_bit
    vq[H & sgni_mask != 0] |= sign_bit

    # --- interleave I/Q and replicate exponents ----------------------------
    vals = np.empty(nfft * 2, dtype=np.int64)
    vals[0::2], vals[1::2] = vi, vq
    exp  = np.repeat(e_orig + shift, 2)             # **use original exponent**

    # --- scale and restore sign -------------------------------------------
    sign = np.where(vals & sign_bit, -1, 1)
    vals &= ~sign_bit                               # strip sign bit

    too_small = exp < e_zero
    neg_exp   = exp < 0

    vals = np.where(too_small, 0, np.where(neg_exp, vals >> (-exp), vals << exp))

    return vals * sign

def resync_to_next_packet(input):
    """
    Resync to the next valid PCAP packet header by scanning byte-by-byte.
    Uses sanity checks on ts_sec, ts_usec, incl_len, and orig_len.
    """
    packet_header_size = 16
    max_seek_bytes = 10 * 1024 * 1024  # Avoid infinite loops on corrupted files
    bytes_scanned = 0

    while True:
        pos = input.tell()
        data = input.read(packet_header_size)
        if len(data) < packet_header_size:
            raise EOFError("Reached end of file during resync")

        try:
            ts_sec, ts_usec, incl_len, orig_len = struct.unpack('<IIII', data)

            now = int(time.time())
            # Sanity checks:
            if (
                2000 <= ts_sec <= now + 3600 and   # reasonable UNIX timestamp (2000+)
                0 <= ts_usec < 1_000_000 and       # microseconds range
                0 < incl_len <= 65535 and
                0 < orig_len <= 65535 and
                incl_len <= orig_len
            ):
                # Looks like a valid packet header
                input.seek(pos)
                return bytes_scanned
        except struct.error:
            pass

        # Move forward by 1 byte
        input.seek(pos + 1)
        bytes_scanned += 1

        if bytes_scanned > max_seek_bytes:
            raise RuntimeError("Resync failed after scanning too many bytes")

class UDPStreamReceiver:
    """Receives UDP packets, stores all data in memory, and supports random access with seek/tell."""

    def __init__(self, host='0.0.0.0', port=5500, max_packet_size=65535, receive_buffer_size_mb=32):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, receive_buffer_size_mb * 1024 * 1024)
        self.sock.bind((host, port))

        self.max_packet_size = max_packet_size
        self.data = bytearray()  # store all received data
        self.pos = 0             # current read position
        self.is_paused = False

    def read(self, size: int) -> bytes:
        # Fill buffer until enough bytes are available from current pos
        while len(self.data) < self.pos + size:
            packet, _ = self.sock.recvfrom(self.max_packet_size)
            if not self.is_paused:
                self.data.extend(packet)

        # Read from current position
        result = self.data[self.pos:self.pos + size]
        self.pos += size
        return bytes(result)

    def tell(self) -> int:
        return self.pos
    
    def close(self):
        self.sock.close()

    def save(self, path):
        """Save the current data to a file."""
        with open(path, 'wb') as f:
            f.write(self.data)

    def clear(self):
        """Clear the in-memory data."""
        self.data.clear()
        self.pos = 0

    def pause(self):
        """Pause receiving data."""
        self.is_paused = True
        
    def resume(self):
        """Resume receiving data."""
        self.is_paused = False

    def seek(self, offset: int, whence: int = 0):
        """Seek to a position in the memory stream."""
        if whence == 0:  # absolute
            new_pos = offset
        elif whence == 1:  # relative
            new_pos = self.pos + offset
        elif whence == 2:  # from end
            new_pos = len(self.data) + offset
        else:
            raise ValueError("Invalid value for whence. Must be 0, 1, or 2.")

        if new_pos < 0:
            raise ValueError("Cannot seek to negative position.")

        # If seeking forward beyond current data, read more until position is reachable
        while new_pos > len(self.data):
            packet, _ = self.sock.recvfrom(self.max_packet_size)
            self.data.extend(packet)

        self.pos = new_pos

class NexmonCSIStreamReader:
    def __init__(self, host='0.0.0.0', port=5500, file=None, simulate_time=False, shift_fft=True, verbose=True, ts_as_datetime=True):
        self.host = host
        self.port = port
        self.receiver = None
        self.file = file
        self.simulate_time = simulate_time
        self.shift_fft = shift_fft
        self.verbose = verbose
        self.ts_as_datetime = ts_as_datetime
    
    def get_name(self) -> str:
        return f"Nexmon CSI Reader {self.host}:{self.port}" if self.file is None else f"Nexmon PCAP File ({self.file})"

    def __iter__(self):
        if self.file:
            data = Path(self.file).read_bytes()
            self.receiver = io.BytesIO(data)
            if self.verbose:
                print(f"Reading from PCAP file: {self.file}")
        else:
            self.receiver = UDPStreamReceiver(host=self.host, port=self.port)
            if self.verbose:
                print(f"Listening on {self.host}:{self.port}...")

        read_pcap_global_header(self.receiver)
        return self._generator()
    
    def _generator(self):
        ts_prev = None
        
        while True:
            try:
                ts, _ = read_pcap_packet_header(self.receiver)
                #read_ethernet_header(self.receiver)
                #read_ip_header(self.receiver)
                read_exact(self.receiver, S_ETH.size + S_IP_MIN.size)  # Skip Ethernet + IP headers
                _, _, udp_len, _ = read_udp_header(self.receiver)
                csi, mac = read_nexmon_csi(self.receiver, udp_len - 8)

                # Simulate real-time pacing
                if ts_prev is not None and self.simulate_time:
                    dt = ts - ts_prev
                    dt = np.clip(dt, 0, 0.005)
                    time.sleep(dt)
                ts_prev = ts

                # Shift zero frequency to center
                if self.shift_fft:
                    csi = np.fft.fftshift(csi)  

                if self.ts_as_datetime:
                    ts = datetime.fromtimestamp(ts)

                yield ts, csi, mac

            except EOFError:
                if self.verbose:
                    print("End of PCAP reached.")
                return
            except Exception as e:
                if self.verbose:
                    print(f" [x] Error reading stream: {e}. Resyncing to next packet...")
                skipped = resync_to_next_packet(self.receiver)
                if self.verbose:
                    print(" [✔] Resynced to next packet OK. Bytes skipped:", skipped)