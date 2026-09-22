"""
SUMO Network & Route File Generator for P25 Traffic Orchestration Network
Generates node, edge, connection, route XML files and produces grid.net.xml and grid.sumocfg.
"""

import os
import subprocess
import xml.etree.ElementTree as ET
from config import SUMO_CONFIG_DIR, GRID_ROWS, GRID_COLS, BENCHMARK_SEEDS

def generate_sumo_xml_files(seed=42, sim_duration=300):
    """
    Generates SUMO network XML configurations for a 2x2 grid junction layout.
    Returns path to the generated .sumocfg file.
    """
    nod_file = os.path.join(SUMO_CONFIG_DIR, "grid.nod.xml")
    edg_file = os.path.join(SUMO_CONFIG_DIR, "grid.edg.xml")
    con_file = os.path.join(SUMO_CONFIG_DIR, "grid.con.xml")
    net_file = os.path.join(SUMO_CONFIG_DIR, "grid.net.xml")
    rou_file = os.path.join(SUMO_CONFIG_DIR, "grid.rou.xml")
    cfg_file = os.path.join(SUMO_CONFIG_DIR, "grid.sumocfg")

    # 1. Generate Nodes (.nod.xml)
    nodes_root = ET.Element("nodes")
    # Internal grid junctions
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            node_id = f"J_{r}_{c}"
            x = c * 300
            y = (GRID_ROWS - 1 - r) * 300
            ET.SubElement(nodes_root, "node", id=node_id, x=str(x), y=str(y), type="traffic_light")
    
    # Boundary nodes for incoming/outgoing traffic
    boundary_nodes = [
        ("N_0", 0, 600), ("N_1", 300, 600),
        ("S_0", 0, -300), ("S_1", 300, -300),
        ("W_0", -300, 300), ("W_1", -300, 0),
        ("E_0", 600, 300), ("E_1", 600, 0)
    ]
    for b_id, x, y in boundary_nodes:
        ET.SubElement(nodes_root, "node", id=b_id, x=str(x), y=str(y), type="priority")

    tree = ET.ElementTree(nodes_root)
    ET.indent(tree, space="  ")
    tree.write(nod_file, encoding="utf-8", xml_declaration=True)

    # 2. Generate Edges (.edg.xml)
    edges_root = ET.Element("edges")
    def add_edge(e_id, from_node, to_node, lanes=2, speed=13.89):
        ET.SubElement(edges_root, "edge", id=e_id, **{"from": from_node, "to": to_node, "numLanes": str(lanes), "speed": str(speed)})

    # Internal edges between grid nodes
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            curr = f"J_{r}_{c}"
            # East neighbor
            if c + 1 < GRID_COLS:
                east = f"J_{r}_{c+1}"
                add_edge(f"e_{curr}_to_{east}", curr, east)
                add_edge(f"e_{east}_to_{curr}", east, curr)
            # South neighbor
            if r + 1 < GRID_ROWS:
                south = f"J_{r+1}_{c}"
                add_edge(f"e_{curr}_to_{south}", curr, south)
                add_edge(f"e_{south}_to_{curr}", south, curr)

    # Boundary edges
    # Top (North)
    add_edge("e_N_0_in", "N_0", "J_0_0")
    add_edge("e_N_0_out", "J_0_0", "N_0")
    add_edge("e_N_1_in", "N_1", "J_0_1")
    add_edge("e_N_1_out", "J_0_1", "N_1")
    # Bottom (South)
    add_edge("e_S_0_in", "S_0", "J_1_0")
    add_edge("e_S_0_out", "J_1_0", "S_0")
    add_edge("e_S_1_in", "S_1", "J_1_1")
    add_edge("e_S_1_out", "J_1_1", "S_1")
    # Left (West)
    add_edge("e_W_0_in", "W_0", "J_0_0")
    add_edge("e_W_0_out", "J_0_0", "W_0")
    add_edge("e_W_1_in", "W_1", "J_1_0")
    add_edge("e_W_1_out", "J_1_0", "W_1")
    # Right (East)
    add_edge("e_E_0_in", "E_0", "J_0_1")
    add_edge("e_E_0_out", "J_0_1", "E_0")
    add_edge("e_E_1_in", "E_1", "J_1_1")
    add_edge("e_E_1_out", "J_1_1", "E_1")

    tree = ET.ElementTree(edges_root)
    ET.indent(tree, space="  ")
    tree.write(edg_file, encoding="utf-8", xml_declaration=True)

    # 3. Generate Route File (.rou.xml)
    routes_root = ET.Element("routes")
    # Define vTypes
    ET.SubElement(routes_root, "vType", id="car", accel="2.6", decel="4.5", length="4.5", maxSpeed="13.89", vClass="passenger", color="0,0,255")
    ET.SubElement(routes_root, "vType", id="bus", accel="1.2", decel="3.5", length="12.0", maxSpeed="11.11", vClass="bus", color="255,255,0")
    ET.SubElement(routes_root, "vType", id="emergency", accel="3.5", decel="5.0", length="6.0", maxSpeed="16.67", vClass="emergency", color="255,0,0")

    # Sample predefined routes
    r1 = ET.SubElement(routes_root, "route", id="r_N_S_0", edges="e_N_0_in e_J_0_0_to_J_1_0 e_S_0_out")
    r2 = ET.SubElement(routes_root, "route", id="r_W_E_0", edges="e_W_0_in e_J_0_0_to_J_0_1 e_E_0_out")
    r3 = ET.SubElement(routes_root, "route", id="r_S_N_1", edges="e_S_1_in e_J_1_1_to_J_0_1 e_N_1_out")
    r4 = ET.SubElement(routes_root, "route", id="r_E_W_1", edges="e_E_1_in e_J_1_1_to_J_1_0 e_W_1_out")

    # Random flow generation based on seed
    import random
    rng = random.Random(seed)
    flow_id = 0
    for step in range(0, sim_duration, 2):
        if rng.random() < 0.65:
            route_choice = rng.choice(["r_N_S_0", "r_W_E_0", "r_S_N_1", "r_E_W_1"])
            vtype_roll = rng.random()
            if vtype_roll < 0.75:
                vtype = "car"
            elif vtype_roll < 0.90:
                vtype = "bus"
            else:
                vtype = "emergency"
            
            ET.SubElement(routes_root, "vehicle", id=f"veh_{flow_id}", type=vtype, route=route_choice, depart=str(step))
            flow_id += 1

    tree = ET.ElementTree(routes_root)
    ET.indent(tree, space="  ")
    tree.write(rou_file, encoding="utf-8", xml_declaration=True)

    # 4. Generate netconvert command if netconvert utility exists
    try:
        cmd = ["netconvert", "--node-files", nod_file, "--edge-files", edg_file, "--output-file", net_file]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    except Exception as e:
        pass  # Will fall back gracefully if netconvert isn't in PATH

    # 5. Generate .sumocfg File
    cfg_root = ET.Element("configuration")
    input_elem = ET.SubElement(cfg_root, "input")
    ET.SubElement(input_elem, "net-file", value="grid.net.xml")
    ET.SubElement(input_elem, "route-files", value="grid.rou.xml")

    time_elem = ET.SubElement(cfg_root, "time")
    ET.SubElement(time_elem, "begin", value="0")
    ET.SubElement(time_elem, "end", value=str(sim_duration))

    tree = ET.ElementTree(cfg_root)
    ET.indent(tree, space="  ")
    tree.write(cfg_file, encoding="utf-8", xml_declaration=True)

    return cfg_file

if __name__ == "__main__":
    path = generate_sumo_xml_files(seed=42, sim_duration=300)
    print(f"Generated SUMO config files at: {path}")
