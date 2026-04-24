import os
import sys
from pathlib import Path
import subprocess

NO_DIFFERENCES_OUTPUT = "NO DIFFERENCES FOUND"

import json, csv

def CreateCSV(FilePath):
    with open(FilePath) as f:
        data = json.load(f)

    summary = data.get('summaryDetails', {}).get('controls', {})

    rows = []
    for result in data.get('results', []):
        resource_id = result.get('resourceID', '')
        for control in result.get('controls', []):
            control_id = control.get('controlID', '')
            ctrl_summary = summary.get(control_id, {})
            counters = ctrl_summary.get('ResourceCounters', {})
            rows.append({
                'FilePath': resource_id,
                'Severity': control.get('severity', ''),
                'Control Name': control.get('name', ''),
                'Failed Resources': counters.get('failedResources', ''),
                'All Resources': counters.get('failedResources', 0) + counters.get('passedResources', 0) + counters.get('excludedResources', 0) + counters.get('skippedResources', 0),
                'Compliance Score': ctrl_summary.get('complianceScore', ''),
            })

    with open('results.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['FilePath','Severity','Control Name','Failed Resources','All Resources','Compliance Score'])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done - {len(rows)} rows written to {FilePath}")

# Deterministic keyword-to-control mapping for Kubescape controls.
KEYWORD_CONTROL_MAP = {
    ("secret", "credential", "password", "token", "apikey", "api_key"): [
        "C-0012: Applications credentials in configuration files",
        "C-0186: Minimize access to secrets",
        "C-0207: Prefer using secrets as files over secrets as environment variables",
    ],
    ("privileged", "allowprivilegeescalation", "non-root", "root", "capab"): [
        "C-0057: Privileged container",
        "C-0016: Allow privilege escalation",
        "C-0013: Non-root containers",
        "C-0200: Minimize the admission of containers with added capabilities",
    ],
    ("network", "ingress", "egress", "hostnetwork", "hostport", "port"): [
        "C-0030: Ingress and Egress blocked",
        "C-0041: HostNetwork access",
        "C-0044: Container hostPort",
        "C-0206: Ensure that all Namespaces have Network Policies defined",
    ],
    ("serviceaccount", "service account", "automount", "mount service principal"): [
        "C-0034: Automatic mapping of service account",
        "C-0190: Ensure that Service Account Tokens are only mounted where necessary",
        "C-0261: ServiceAccount token mounted",
    ],
    ("resource", "cpu", "memory", "limit", "request"): [
        "C-0268: Ensure CPU requests are set",
        "C-0269: Ensure memory requests are set",
        "C-0270: Ensure CPU limits are set",
        "C-0271: Ensure memory limits are set",
    ],
    ("image", "registry", "latest", "signature"): [
        "C-0078: Images from allowed registry",
        "C-0075: Image pull policy on latest tag",
        "C-0236: Verify image signature",
    ],
    ("rbac", "role", "clusterrole", "cluster-admin", "admin"): [
        "C-0035: Administrative Roles",
        "C-0185: Ensure that the cluster-admin role is only used where required",
        "C-0187: Minimize wildcard use in Roles and ClusterRoles",
    ],
    ("namespace", "default namespace"): [
        "C-0212: The default namespace should not be used",
        "C-0061: Pods in default namespace",
    ],
    ("hostpath", "runtime socket", "docker.sock", "containerd.sock", "socket"): [
        "C-0048: HostPath mount",
        "C-0074: Container runtime socket mounted",
        "C-0203: Minimize the admission of HostPath volumes",
    ],
}

FALLBACK_CONTROLS = [
    "C-0211: Apply Security Context to Your Pods and Containers",
    "C-0186: Minimize access to secrets",
    "C-0206: Ensure that all Namespaces have Network Policies defined",
]


def readFile(filePath):
    outputLines = []
    with open(filePath, "r", encoding="utf-8") as file:
        for line in file:
            outputLines.append(line.strip())
    return outputLines


def _is_no_difference_line(line: str) -> bool:
    return "NO DIFFERENCES" in line.upper()


def _extract_differences(lines: list[str]) -> list[str]:
    return [line for line in lines if line and not _is_no_difference_line(line)]


def _contains_no_difference_marker(lines: list[str]) -> bool:
    return any(_is_no_difference_line(line) for line in lines)


def _dedupe_keep_order(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _normalize_non_empty_lines(lines: list[str]) -> list[str]:
    return [line.strip() for line in lines if line and line.strip()]


def _symmetric_line_differences(lines1: list[str], lines2: list[str]) -> list[str]:
    """Return unique line differences while preserving first-seen order."""
    set1 = set(lines1)
    set2 = set(lines2)
    diff = [line for line in lines1 if line not in set2]
    diff.extend(line for line in lines2 if line not in set1)
    return _dedupe_keep_order(diff)


def map_differences_to_controls(differences: list[str]) -> list[str]:
    if not differences:
        return []

    combined = " ".join(differences).lower()
    mapped_controls: list[str] = []
    for keywords, controls in KEYWORD_CONTROL_MAP.items():
        if any(keyword in combined for keyword in keywords):
            mapped_controls.extend(controls)

    if not mapped_controls:
        mapped_controls = FALLBACK_CONTROLS.copy()

    return _dedupe_keep_order(mapped_controls)


def compare_two_text_files_and_map_controls(
    txt_path_1: str, txt_path_2: str, output_txt_path: str
) -> list[str]:
    """Compare two TXT files and write either mapped controls or NO DIFFERENCES FOUND."""
    lines_1 = _normalize_non_empty_lines(readFile(txt_path_1))
    lines_2 = _normalize_non_empty_lines(readFile(txt_path_2))

    differences = _symmetric_line_differences(lines_1, lines_2)

    if differences:
        output_lines = map_differences_to_controls(differences)
    else:
        output_lines = [NO_DIFFERENCES_OUTPUT]

    with open(output_txt_path, "w", encoding="utf-8") as file:
        file.write("\n".join(output_lines))

    return output_lines


def determine_difference_controls(
    elements_txt_path: str, requirements_txt_path: str, output_txt_path: str
) -> list[str]:
    """Write Kubescape controls mapped to discovered differences across two TXT reports.

    The two input files are expected to be difference-report files from previous steps:
    one for element differences and one for requirement differences.
    """
    element_lines = readFile(elements_txt_path)
    requirement_lines = readFile(requirements_txt_path)

    element_differences = _extract_differences(element_lines)
    requirement_differences = _extract_differences(requirement_lines)
    differences = element_differences + requirement_differences

    # Respect explicit "no differences" markers from the comparator output format.
    explicit_no_differences = (
        _contains_no_difference_marker(element_lines)
        and _contains_no_difference_marker(requirement_lines)
        and not differences
    )

    if differences and not explicit_no_differences:
        output_lines = map_differences_to_controls(differences)
    else:
        output_lines = [NO_DIFFERENCES_OUTPUT]

    with open(output_txt_path, "w", encoding="utf-8") as file:
        file.write("\n".join(output_lines))

    return output_lines


def _resolve_input_path(path_arg: str) -> str:
    if os.path.isfile(path_arg):
        return path_arg
    txt_candidate = os.path.join("TXTs", path_arg+".txt")
    return txt_candidate if os.path.isfile(txt_candidate) else path_arg


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(
            "Usage: python task3Exectutor.py <elements_txt> <requirements_txt> [output_txt]"
        )

    elements_path = _resolve_input_path(sys.argv[1])
    requirements_path = _resolve_input_path(sys.argv[2])

    if len(sys.argv) >= 4:
        output_path = sys.argv[3]
    else:
        output_name = f"{Path(elements_path).stem} {Path(requirements_path).stem} controls.txt"
        output_path = os.path.join("TXTs", output_name)

    determine_difference_controls(elements_path, requirements_path, output_path)
    # run the kubescape
    result = subprocess.run(["bash", "kubeScapeRun.sh", "kubeScape.txt"], capture_output=True, text=True)
    #convert to CSV
    CreateCSV("results.json")