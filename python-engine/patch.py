import sys
import time

file_path = 'main.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
for i, line in enumerate(lines):
    if line.strip().startswith('# -- LAYER 1: OCR'):
        start_idx = i
        break

if start_idx != -1:
    end_idx = -1
    for i in range(start_idx, len(lines)):
        if 'return ScanResponse(' in lines[i]:
            for j in range(i, len(lines)):
                if ')' in lines[j] and 'diagnostics=' in lines[j-1]:
                    end_idx = j + 1
                    break
            break
    
    if end_idx != -1:
        new_lines = lines[:start_idx]
        new_lines.append('    try:\n')
        for i in range(start_idx, end_idx):
            new_lines.append('    ' + lines[i])
        
        new_lines.append('    except Exception as e:\n')
        new_lines.append('        import traceback\n')
        new_lines.append('        traceback.print_exc()\n')
        new_lines.append('        diagnostics["Pipeline_Error"] = str(e)\n')
        new_lines.append('        return ScanResponse(\n')
        new_lines.append('            detections=[], words=[], fullText="",\n')
        new_lines.append('            processingTime=int((time.time() - t0) * 1000),\n')
        new_lines.append('            aiDescription="", privacyScore=100,\n')
        new_lines.append('            metrics=SystemMetrics(ocr_latency_ms=0, total_latency_ms=int((time.time() - t0) * 1000), redaction_coverage_pct=0.0, memory_usage_mb=0.0),\n')
        new_lines.append('            diagnostics=diagnostics\n')
        new_lines.append('        )\n')
        
        new_lines.extend(lines[end_idx:])
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print('Successfully wrapped with try-except')
    else:
        print('End index not found')
else:
    print('Start index not found')
