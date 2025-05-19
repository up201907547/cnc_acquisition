import socket
import struct

# Struct format: 6 floats, 1 uint64, 3 ints
# Adjust if your DadosAtom struct differs
DADOS_STRUCT_FORMAT = "<6fQ3i"  # Little-endian

def connect_and_receive(ip="192.168.4.1", port=1234):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, port))
    print(f"Connected to {ip}:{port}")

    struct_size = struct.calcsize(DADOS_STRUCT_FORMAT)
    try:
        while True:
            data = s.recv(struct_size)
            if len(data) < struct_size:
                print("Incomplete data received, connection may be closing.")
                break

            ax, ay, az, gx, gy, gz, timestamp, package, index, isDone = struct.unpack(DADOS_STRUCT_FORMAT, data)

            print(f"Accel: ({ax:.2f}, {ay:.2f}, {az:.2f}) | Gyro: ({gx:.2f}, {gy:.2f}, {gz:.2f}) | Time: {timestamp} | Pkg: {package} | Idx: {index} | Done: {isDone}")
    except KeyboardInterrupt:
        print("Disconnected.")
    finally:
        s.close()

if __name__ == "__main__":
    connect_and_receive()