"""
Scenario Generator for P25 Multi-Modal Traffic Orchestration Network.
Generates SUMO network files (.net.xml, .rou.xml, .sumocfg) for an interconnected 2x2 grid.
Supports passenger cars, public transit buses, and emergency vehicles.
"""

import os
import random
import xml.etree.ElementTree as ET
from xml.dom import minidom

def prettify_xml(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def generate_network_xml(output_dir="sumo_files"):
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Node XML (nodes.nod.xml)
    nodes_root = ET.Element("nodes")
    # Intersections (internal traffic light nodes)
    junctions = ["J0_0", "J0_1", "J1_0", "J1_1"]
    coords = {
        "J0_0": (250, 250),
        "J0_1": (500, 250),
        "J1_0": (250, 500),
        "J1_1": (500, 500)
    }
    for j_id, (x, y) in coords.items():
        ET.SubElement(nodes_root, "node", id=j_id, x=str(x), y=str(y), type="traffic_light")
        
    # Boundary perimeter nodes
    perimeters = {
        "W0": (0, 250), "W1": (0, 500),
        "E0": (750, 250), "E1": (750, 500),
        "S0": (250, 0), "S1": (500, 0),
        "N0": (250, 750), "N1": (500, 750)
    }
    for p_id, (x, y) in perimeters.items():
        ET.SubElement(nodes_root, "node", id=p_id, x=str(x), y=str(y), type="priority")
        
    with open(os.path.join(output_dir, "network.nod.xml"), "w", encoding="utf-8") as f:
        f.write(prettify_xml(nodes_root))

    # 2. Edges XML (edges.edg.xml)
    edges_root = ET.Element("edges")
    edge_list = [
        # West boundaries
        ("W0_to_J0_0", "W0", "J0_0"), ("J0_0_to_W0", "J0_0", "W0"),
        ("W1_to_J1_0", "W1", "J1_0"), ("J1_0_to_W1", "J1_0", "W1"),
        # East boundaries
        ("J0_1_to_E0", "J0_1", "E0"), ("E0_to_J0_1", "E0", "J0_1"),
        ("J1_1_to_E1", "J1_1", "E1"), ("E1_to_J1_1", "E1", "J1_1"),
        # South boundaries
        ("S0_to_J0_0", "S0", "J0_0"), ("J0_0_to_S0", "J0_0", "S0"),
        ("S1_to_J0_1", "S1", "J0_1"), ("J0_1_to_S1", "J0_1", "S1"),
        # North boundaries
        ("J1_0_to_N0", "J1_0", "N0"), ("N0_to_J1_0", "N0", "J1_0"),
        ("J1_1_to_N1", "J1_1", "N1"), ("N1_to_J1_1", "N1", "J1_1"),
        # Inter-junction horizontal links
        ("J0_0_to_J0_1", "J0_0", "J0_1"), ("J0_1_to_J0_0", "J0_1", "J0_0"),
        ("J1_0_to_J1_1", "J1_0", "J1_1"), ("J1_1_to_J1_0", "J1_1", "J1_0"),
        # Inter-junction vertical links
        ("J0_0_to_J1_0", "J0_0", "J1_0"), ("J1_0_to_J0_0", "J1_0", "J0_0"),
        ("J0_1_to_J1_1", "J0_1", "J1_1"), ("J1_1_to_J0_1", "J1_1", "J0_1")
    ]
    for e_id, from_n, to_n in edge_list:
        ET.SubElement(edges_root, "edge", id=e_id, from_node=from_n, to_node=to_n,
                       numLanes="2", speed="13.89", priority="1")
                       
    with open(os.path.join(output_dir, "network.edg.xml"), "w", encoding="utf-8") as f:
        f.write(prettify_xml(edges_root))

    return junctions, edge_list

def generate_routes_xml(output_dir="sumo_files", seed=42, total_steps=360):
    os.makedirs(output_dir, exist_ok=True)
    random.seed(seed)
    
    routes_root = ET.Element("routes")
    
    # Define vehicle types with multi-modal characteristics
    # 1. Standard Passenger Car
    ET.SubElement(routes_root, "vType", id="car", accel="2.6", decel="4.5",
                  sigma="0.5", length="4.8", maxSpeed="13.89", guiShape="passenger", color="0,0.8,1")
    # 2. Public Transit Bus (longer, heavier priority)
    ET.SubElement(routes_root, "vType", id="bus", accel="1.5", decel="3.5",
                  sigma="0.3", length="12.0", maxSpeed="11.11", guiShape="bus", color="1,0.8,0")
    # 3. Emergency Vehicle (high acceleration, siren)
    ET.SubElement(routes_root, "vType", id="emergency", accel="3.5", decel="5.0",
                  sigma="0.1", length="6.5", maxSpeed="16.67", guiShape="emergency", color="1,0,0")

    # Major arterial routes traversing the 2x2 grid
    standard_routes = [
        # West to East corridors
        ("r_W0_E0", "W0_to_J0_0 J0_0_to_J0_1 J0_1_to_E0"),
        ("r_W1_E1", "W1_to_J1_0 J1_0_to_J1_1 J1_1_to_E1"),
        # East to West corridors
        ("r_E0_W0", "E0_to_J0_1 J0_1_to_J0_0 J0_0_to_W0"),
        ("r_E1_W1", "E1_to_J1_1 J1_1_to_J1_0 J1_0_to_W1"),
        # South to North corridors
        ("r_S0_N0", "S0_to_J0_0 J0_0_to_J1_0 J1_0_to_N0"),
        ("r_S1_N1", "S1_to_J0_1 J0_1_to_J1_1 J1_1_to_N1"),
        # North to South corridors
        ("r_N0_S0", "N0_to_J1_0 J1_0_to_J0_0 J0_0_to_S0"),
        ("r_N1_S1", "N1_to_J1_1 J1_1_to_J0_1 J0_1_to_S1")
    ]
    
    for r_id, edges in standard_routes:
        ET.SubElement(routes_root, "route", id=r_id, edges=edges)
        
    # Generate multi-modal vehicle departures
    veh_count = 0
    for step in range(1, total_steps, 2):
        for r_id, _ in standard_routes:
            # Deterministic probability driven by seed
            p = random.random()
            if p < 0.35: # Passenger Car
                veh_count += 1
                ET.SubElement(routes_root, "vehicle", id=f"veh_{veh_count}",
                              type="car", route=r_id, depart=str(step), departLane="best")
            elif p < 0.42: # Public Transit Bus
                veh_count += 1
                ET.SubElement(routes_root, "vehicle", id=f"bus_{veh_count}",
                              type="bus", route=r_id, depart=str(step), departLane="best")
            elif p < 0.44: # Emergency Vehicle
                veh_count += 1
                ET.SubElement(routes_root, "vehicle", id=f"emerg_{veh_count}",
                              type="emergency", route=r_id, depart=str(step), departLane="best")
                              
    route_file = os.path.join(output_dir, f"routes_seed_{seed}.rou.xml")
    with open(route_file, "w", encoding="utf-8") as f:
        f.write(prettify_xml(routes_root))
        
    # Also write default routes.rou.xml
    with open(os.path.join(output_dir, "routes.rou.xml"), "w", encoding="utf-8") as f:
        f.write(prettify_xml(routes_root))

    # Generate .sumocfg
    cfg_root = ET.Element("configuration")
    input_elem = ET.SubElement(cfg_root, "input")
    ET.SubElement(input_elem, "net-file", value="network.net.xml")
    ET.SubElement(input_elem, "route-files", value="routes.rou.xml")
    time_elem = ET.SubElement(cfg_root, "time")
    ET.SubElement(time_elem, "begin", value="0")
    ET.SubElement(time_elem, "end", value=str(total_steps))
    
    with open(os.path.join(output_dir, "network.sumocfg"), "w", encoding="utf-8") as f:
        f.write(prettify_xml(cfg_root))

    return route_file, veh_count

if __name__ == "__main__":
    generate_network_xml()
    generate_routes_xml(seed=42)
    print("Scenario generation completed successfully.")
