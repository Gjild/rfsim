import numpy as np
from utils.matrix import z_to_s, s_to_z

def test_z_to_s_and_back():
    # Define a two-port impedance matrix for a resistor:
    # Z = [[R, -R], [-R, R]]
    R = 1000
    Z = np.array([[R, -R],
                  [-R, R]], dtype=complex)
    Z0 = 50
    # Convert to scattering parameters.
    S = z_to_s(Z, Z0=Z0)
    # Convert back to impedance parameters.
    Z_reconstructed = s_to_z(S, Z0=Z0)
    # Verify that Z_reconstructed is approximately equal to Z.
    np.testing.assert_allclose(Z, Z_reconstructed, rtol=1e-5, atol=1e-5)

def test_s_to_z_and_back():
    # Define a two-port scattering matrix.
    S = np.array([[0, 0.5],
                  [0.5, 0]], dtype=complex)
    Z0 = 50
    # Convert to impedance.
    Z = s_to_z(S, Z0=Z0)
    # Convert back to scattering.
    S_reconstructed = z_to_s(Z, Z0=Z0)
    np.testing.assert_allclose(S, S_reconstructed, rtol=1e-5, atol=1e-5)
