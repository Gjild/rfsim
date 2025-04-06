# RFSim

A Python-based RF circuit simulator that supports symbolic parameter resolution, multi-parameter sweeps, and circuit analysis using Modified Nodal Analysis (MNA) techniques.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Examples](#examples)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)

## Overview

## Overview

RFSim is a Python-based RF circuit simulator designed to simplify the analysis and design of radio frequency circuits. It leverages Modified Nodal Analysis (MNA) techniques to accurately simulate circuit behavior while supporting symbolic parameter resolution. By using a modular architecture, RFSim allows users to define circuits using YAML-based netlist and sweep configuration files, enabling flexible and rapid prototyping. The simulator converts between impedance (Z), admittance (Y), and scattering (S) parameters, providing a toolkit for RF circuit analysis and optimization.

## Features

- **Modular Component Architecture:**  
  RFSim supports a range of RF components including resistors, capacitors, inductors, and transmission lines. The design leverages a component factory and dynamic registration, making it easy to add or extend components.

- **Symbolic Parameter Resolution:**  
  The simulator uses symbolic computation via Sympy along with Pint for unit conversion, enabling the evaluation of complex, nested parameter expressions and ensuring consistency across units.

- **Robust Matrix Conversions:**  
  Provides comprehensive utilities to convert between impedance (Z), admittance (Y), and scattering (S) parameters. These functions include robust inversion methods to handle singular or ill-conditioned matrices, ensuring numerical stability.

- **YAML-based Configuration:**  
  Circuit netlists and sweep configurations are defined using human-readable YAML files, allowing for intuitive and flexible simulation setups.

- **Parallel Sweep Evaluations:**  
  RFSim leverages parallel processing (using ProcessPoolExecutor) to evaluate multiple sweep points simultaneously, significantly improving performance for large-scale parameter sweeps.

- **Comprehensive Testing Suite:**  
  The project includes extensive unit, integration, and performance tests that cover component behavior, topology management, parameter resolution, and concurrency, ensuring reliability and ease of maintenance.

- **Extensible and Scalable Design:**  
  With its modular architecture and dynamic component registration, RFSim is designed to be easily extended and scaled for more complex RF simulation needs.


## Installation

*Provide instructions on how to install the simulator, including dependencies.*

```bash
# Clone the repository
git clone <repository-url>

# Change directory into the project
cd rfsim

# Install dependencies (preferably in a virtual environment)
pip install -r requirements.txt

```

## Usage

To run a simulation with RFSim, you need to provide two YAML configuration files: one for the netlist (defining components, parameters, and connections) and one for the sweep settings (defining frequency and parameter sweeps).

### Netlist YAML

The netlist file describes the circuit elements, their parameters, and how they are connected. For example, a simple netlist might look like:

```yaml
parameters:
  scale: 1.0
external_ports:
  - p1
  - p2
components:
  - id: R1
    type: resistor
    params:
      R: "1000"
    ports: ["1", "2"]
  - id: C1
    type: capacitor
    params:
      C: "1e-9"
    ports: ["1", "2"]
connections:
  - port: R1.1
    node: p1
  - port: R1.2
    node: n1
  - port: C1.1
    node: n1
  - port: C1.2
    node: p2
```

### Sweep YAML

The sweep file defines the parameters that will be varied during the simulation. An example sweep configuration is:

```yaml
sweep:
  - param: f
    range: [1e6, 10e6]
    points: 10
    scale: linear
  - param: scale
    values: [1.0, 2.0]
```

### Running the Simulation

The main entry point for running a sweep simulation is the `run_sweep.py` script. You can invoke it from the command line with the following options:

- `--netlist`: Path to the YAML netlist file.
- `--sweep`: Path to the YAML sweep configuration file.
- `--dump` (optional): Path to dump the sweep results (e.g., `sweep.npz`).
- `--summary`: Print a summary of the sweep results.
- `--verbose`: Enable detailed logging for debugging.

#### Example Command

```bash
python run_sweep.py --netlist path/to/netlist.yaml --sweep path/to/sweep.yaml --summary --verbose
```

When you run this command, RFSim will:
1. Parse and validate the netlist and sweep configuration.
2. Construct the circuit and set up the simulation based on the provided parameters.
3. Execute the sweep evaluation, potentially in parallel, to compute the scattering matrices for each frequency point.
4. Print a summary of the simulation results and any errors encountered.
5. Optionally, dump the full results to a file if the `--dump` flag is provided.

Be sure to check the provided YAML examples for a detailed reference on how to format your configuration files.


## Examples

Below are some examples of how to configure and run simulations using RFSim.

### Example 1: Basic Netlist and Sweep Configuration

**Netlist (default_netlist.yml):**

```yaml
parameters:
  scale: 1.0

external_ports:
  - p1
  - p2

components:
  - id: R1
    type: resistor
    params:
      R: "1000"
    ports: ["1", "2"]

connections:
  - port: R1.1
    node: p1
  - port: R1.2
    node: p2
```

This netlist defines a simple circuit with one resistor (R1) whose resistance is set to 1000 Ohms. The resistor’s two ports are connected to external nodes `p1` and `p2`.

**Sweep Configuration (default_sweep.yml):**

```yaml
sweep:
  - param: f
    range: [1e6, 10e6]
    points: 10
    scale: "linear"
```

The sweep configuration specifies a frequency sweep (`f`) from 1 MHz to 10 MHz over 10 points using a linear scale.

---

## Testing

This project includes an extensive test suite to ensure the simulator's reliability and performance. The tests cover:

- **Component Impedance Calculations:**  
  Validates the impedance functions for capacitors, inductors, resistors, etc., including edge cases such as zero frequency and negative values.

- **Matrix Conversions:**  
  Tests the conversion routines between impedance (Z), admittance (Y), and scattering (S) matrices, including robust inversion and round-trip consistency.

- **Symbolic Parameter Resolution:**  
  Ensures that symbolic expressions, dependency resolution, and unit conversions work as expected.

- **YAML Parsing & Integration:**  
  Checks netlist and sweep configuration parsing, schema validation, and full circuit integration.

- **Circuit Topology & Evaluation:**  
  Validates circuit connectivity, topology consistency, and parallel sweep evaluation, including performance and error handling.

- **Performance & Concurrency:**  
  Benchmarks sweep evaluations and verifies stability under concurrent processing.

### Running Tests

All tests are organized in the `tests/` directory. To run the complete test suite, use:

```bash
pytest
```

For more verbose output, run:

```bash
pytest -v
```

If you want to run only performance benchmarks (ensure the optional benchmark tests are enabled), use:

```bash
pytest --benchmark-only
```

These tests will help ensure that new changes do not break existing functionality and that the simulator continues to meet its performance requirements. If you encounter any failures or unexpected behavior, please refer to the log output for debugging information.

```markdown
rfsim/
├── components/
│   ├── __init__.py
│   │   Contains package initialization code.
│   ├── capacitor.py
│   │   Implements the **CapacitorComponent** class that computes capacitor impedance 
│   │   using the formula: 1/(j2πfC). It inherits from a common single impedance component base.
│   ├── factory.py
│   │   Provides functions to retrieve and register components via a registry. 
│   │   Uses the type_name attribute of each component class for lookup.
│   ├── inductor.py
│   │   Implements the **InductorComponent** class that computes the impedance of an inductor 
│   │   (j2πfL).
│   ├── resistor.py
│   │   Implements the **ResistorComponent** class which returns a resistor’s resistance value 
│   │   (frequency independent).
│   ├── single_impedance_component.py
│   │   Defines the base class for single impedance components (e.g., resistor, capacitor, inductor). 
│   │   It handles the merging of default and user parameters, Y-matrix stamping (for MNA), and 
│   │   provides a placeholder for the impedance expression.
│   ├── transmission_line.py
│   │   Implements the **TransmissionLineComponent** class. This class computes the scattering (S) 
│   │   and admittance (Y) matrices for transmission lines using the line’s physical parameters.
│   └── two_port_mixin.py
│       Provides mixin classes to build two-port impedance/admittance submatrices. 
│       Contains:
│       - **SeriesTwoPortZMixin** and **ShuntTwoPortZMixin** for impedance stamping.
│       - **SeriesTwoPortYMNAStamp** and **ShuntTwoPortYMNAStamp** for admittance (Y) stamping.
│
├── core/
│   ├── behavior/
│   │   └── component.py
│   │       Defines the abstract **Component** class and the **TwoPortComponent** subclass. 
│   │       Includes methods for obtaining S and Z matrices, cloning components, and YAML serialization.
│   │
│   ├── circuit_serializer.py
│   │   Contains functions to convert a **Circuit** object into a YAML-friendly dictionary 
│   │   (and write it to file), preserving components, parameters, and connection details.
│   │
│   ├── evaluation_types.py
│   │   Defines data classes such as **EvaluationPoint** to represent individual sweep evaluation 
│   │   results and associated parameters.
│   │
│   ├── evaluator.py
│   │   Implements the circuit evaluation strategy. It assembles the global nodal Y matrix from 
│   │   all components, performs node reduction (if external ports are defined), and converts 
│   │   the reduced Y matrix into an S matrix.
│   │
│   ├── exceptions.py
│   │   Contains custom exception classes like **RFSimError**, **ParameterError**, **TopologyError**, 
│   │   **ComponentEvaluationError**, and **SubcircuitMappingError**.
│   │
│   ├── flattening_engine.py
│   │   Implements routines to flatten a hierarchical subcircuit (a **Subcircuit** instance) into 
│   │   a flat **Circuit**. It clones the internal circuit, remaps nodes based on the external 
│   │   interface, and updates component connections.
│   │
│   ├── subcircuit/
│   │   └── subcircuit.py
│   │       Implements the **Subcircuit** class, which encapsulates a hierarchical circuit. 
│   │       It defines methods to compute S and Z matrices from the internal circuit and supports 
│   │       flattening.
│   │
│   ├── topology/
│   │   ├── circuit.py
│   │   │   Defines the **Circuit** class, which is the container for components, parameters, 
│   │   │   the topology manager, and evaluation routines. It also includes methods to add, remove, 
│   │   │   or update components.
│   │   ├── node.py
│   │   │   Implements the **Node** class that represents a circuit node. Nodes have properties 
│   │   │   such as name, ground status, and net class.
│   │   └── port.py
│   │       Defines the **Port** class that represents a connection point on a component. 
│   │       Ports keep track of their index, name, and which node they are connected to.
│   │
│   └── topology_manager.py
│       Manages the overall circuit topology, keeping track of nodes and their connections 
│       through a NetworkX MultiGraph. It includes methods to add/remove nodes, connect/disconnect 
│       ports, and update topology information based on component connections.
│
├── default_netlist.yml
│   A sample YAML file containing a basic netlist. It specifies components (e.g., a resistor), 
│   their parameters, ports, and connection definitions.
│
├── default_sweep.yml
│   A sample YAML file for configuring a parameter sweep (typically a frequency sweep). 
│   It defines the sweep range, number of points, and scale (linear or logarithmic).
│
├── evaluation/
│   └── sweep.py
│       Implements the sweep simulation routines. It defines functions to evaluate individual 
│       sweep points (in parallel using ProcessPoolExecutor), batch evaluations, and aggregate 
│       results into a **SweepResult**.
│
├── examples/
│   Contains additional example configurations and netlists that demonstrate how to set up 
│   and run simulations.
│
├── inout/
│   └── yaml_parser.py
│       Contains functions to parse and validate YAML files for netlists and sweep configurations. 
│       Uses the Cerberus library to validate the YAML schema and creates a **Circuit** object 
│       from the parsed data.
│
├── pyproject.toml
│   Project configuration file that defines metadata (name, version, description), the required 
│   Python version, and all dependency versions.
│
├── run_sweep.py
│   The main executable script to run a sweep simulation. It parses command-line arguments for 
│   netlist and sweep YAML files, sets up logging, validates the circuit, executes the sweep, 
│   and optionally dumps results.
│
├── symbolic/
│   Contains modules for symbolic computation and parameter resolution.
│   ├── constants.py
│   │   Defines default values for common components and simulation parameters.
│   ├── dependency_resolver.py
│   │   Implements functions to build a dependency graph for parameters and perform a topological 
│   │   sort to determine the correct evaluation order.
│   ├── evaluator.py
│   │   Provides functions for symbolic evaluation of parameter expressions using sympy. It compiles 
│   │   expressions and evaluates them with previously resolved parameters.
│   ├── expressions.py
│   │   Contains helper functions to compile symbolic expressions into sympy objects and corresponding 
│   │   numerical functions.
│   ├── parameters_.py
│   │   Implements the core logic for resolving parameter expressions, merging parameter dictionaries, 
│   │   caching compiled lambdas for performance, and handling unit conversions.
│   ├── units.py
│   │   Provides functions to parse physical quantities (using Pint) and check if strings represent 
│   │   numeric values.
│   └── utils.py
│       Contains miscellaneous utility functions for symbolic operations, such as merging parameter 
│       dictionaries with conflict strategies.
│
├── test_yamls/
│   Contains sample YAML files used for testing netlist parsing and sweep configuration.
│   ├── netlist.yaml
│   │   An example netlist defining several components (capacitors and inductors), external ports, 
│   │   and connection mappings.
│   ├── netlist.yaml.bak
│   │   A backup version of a netlist file with alternate parameter values for comparison.
│   └── sweep.yaml
│       An example sweep configuration defining a frequency sweep and additional parameter sweeps.
│
├── tests/
│   Contains a comprehensive suite of unit, integration, and performance tests.
│   ├── conftest.py
│   │   Provides pytest fixtures for basic and complex circuit setups, as well as a dummy logger.
│   ├── test_circuit.py
│   │   Tests basic circuit operations like adding, removing, and updating components.
│   ├── test_component_and_matrix_improvements.py
│   │   Tests for component impedance calculations (capacitors, inductors, resistors) and matrix 
│   │   utility functions.
│   ├── test_components.py
│   │   Verifies individual component impedance expressions and behavior under edge cases.
│   ├── test_concurrency_performance_improvements.py
│   │   Tests parallel sweep evaluation performance, error propagation in concurrent runs, and 
│   │   stability.
│   ├── test_factory.py
│   │   Validates the component factory functions including component registration and lookup.
│   ├── test_flattening_engine_improvements.py
│   │   Tests the flattening of hierarchical subcircuits, ensuring node renaming and interface 
│   │   mapping work correctly.
│   ├── test_integration.py
│   │   Integration tests that combine YAML parsing, circuit evaluation, and serialization.
│   ├── test_matrix_utils.py
│   │   Tests for matrix conversion utilities (robust inversion, Z↔S, Y↔S conversions) under 
│   │   various conditions.
│   ├── test_parameter_resolution_edge_cases.py
│   │   Tests for symbolic parameter resolution covering nested dependencies, unit conversions, 
│   │   and error conditions.
│   ├── test_performance.py
│   │   Performance benchmarks for sweep simulations, ensuring that large batches run within time 
│   │   limits.
│   ├── test_subcircuit.py
│   │   Tests for subcircuit functionality including flattening and matrix extraction.
│   ├── test_sweep.py
│   │   Tests for the sweep evaluation routines, including multi-parameter sweeps and error propagation.
│   ├── test_symbolic.py
│   │   Tests for basic and advanced symbolic expression resolution using sympy.
│   ├── test_symbolic_utils.py
│   │   Additional tests covering symbolic operations, unit conversions, and function evaluations.
│   ├── test_topology_edge_cases.py
│   │   Tests for detecting topology issues such as self-loops, duplicate nodes, and disconnected graphs.
│   ├── test_topology_manager.py
│   │   Tests for the TopologyManager’s functionality, including node management and port connection updates.
│   └── test_yaml_parser.py
│       Tests YAML parsing and schema validation for both netlist and sweep configuration files.
│
└── utils/
    ├── logging_config.py
    │   Configures logging for the application, setting up console and file handlers with a standard format.
    ├── matrix.py
    │   Provides functions for robust matrix inversion (with regularization) and conversions between 
    │   impedance (Z), scattering (S), and admittance (Y) matrices.
    ├── tags.py
    │   Implements a centralized tag registry for generating unique widget tags (useful for frontend or GUI integrations).
    └── touchstone.py
        Contains a stub implementation for exporting sweep results (S-parameters) to a Touchstone (.s2p) file.

```
## Contributing

This project is a personal initiative, and at this time, contributions are managed exclusively by me. If you have suggestions or ideas for improvements, please feel free to reach out directly via the project's issue tracker or contact me directly. While pull requests are not being actively accepted from external contributors at this moment, I welcome discussion on any potential enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
