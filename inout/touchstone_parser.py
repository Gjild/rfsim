import numpy as np

def read_touchstone_file(filename: str) -> dict:
    """
    Reads a 2-port touchstone (.s2p) file.
    
    Expected file format (ignoring comment lines):
      # Hz S RI R 50
      f   Re(S11) Im(S11) Re(S21) Im(S21) Re(S12) Im(S12) Re(S22) Im(S22)
      
    Returns:
        A dictionary with two keys:
          - "freq": A numpy array of frequency values.
          - "S": A list of 2x2 complex numpy arrays (S-parameter matrices).
          
    Raises:
        ValueError: If no valid data is found or if parsing fails.
    """
    freq_list = []
    S_list = []
    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            tokens = line.split()
            # Expect frequency and 8 numbers (4 complex numbers)
            if len(tokens) != 9:
                continue  # Skip lines not matching expected format.
            try:
                f_val = float(tokens[0])
                S11 = float(tokens[1]) + 1j * float(tokens[2])
                S21 = float(tokens[3]) + 1j * float(tokens[4])
                S12 = float(tokens[5]) + 1j * float(tokens[6])
                S22 = float(tokens[7]) + 1j * float(tokens[8])
            except Exception as e:
                raise ValueError(f"Error parsing line '{line}': {e}")
            S_matrix = np.array([[S11, S12],
                                 [S21, S22]], dtype=complex)
            freq_list.append(f_val)
            S_list.append(S_matrix)
    if not freq_list:
        raise ValueError("No valid data found in touchstone file.")
    return {"freq": np.array(freq_list), "S": S_list}
