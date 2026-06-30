import sys

file_path = r'D:\rot post\privacy-guardian\python-engine\main.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if '# -- CONCURRENT MODEL EXECUTION' in line:
        start_idx = i
    if 'return ScanResponse(' in line and start_idx != -1 and end_idx == -1:
        # Find the end of ScanResponse
        for j in range(i, len(lines)):
            if ')' in lines[j] and 'diagnostics=diagnostics' in lines[j-1]:
                end_idx = j + 1
                break

if start_idx == -1 or end_idx == -1:
    print('Could not find section')
    sys.exit(1)

NEW_BLOCK = """        # -- 4-WAY TILING ENGINE ----------------------------------------------------
        import concurrent.futures
        t_start = time.time()
        
        # Split image into 4 exact quadrants
        mid_y, mid_x = H // 2, W // 2
        patches = [
            (img[0:mid_y, 0:mid_x], 0, 0, mid_x, mid_y),            # TL
            (img[0:mid_y, mid_x:W], mid_x, 0, W - mid_x, mid_y),    # TR
            (img[mid_y:H, 0:mid_x], 0, mid_y, mid_x, H - mid_y),    # BL
            (img[mid_y:H, mid_x:W], mid_x, mid_y, W - mid_x, H - mid_y) # BR
        ]

        def process_patch(patch_data):
            patch_img, off_x_px, off_y_px, pW, pH = patch_data
            
            # Preprocess for OCR
            gray = cv2.cvtColor(patch_img, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            img_enhanced = cv2.cvtColor(clahe.apply(gray), cv2.COLOR_GRAY2BGR)

            # Sequential processing per patch to avoid thread chaos
            lines = run_ocr(img_enhanced)
            face_d = run_faces(patch_img, pW, pH)
            qr_d = run_qr(patch_img, pW, pH)
            yolo_d = run_yolo(patch_img, pW, pH)
            nsfw_d = run_nudenet(patch_img, pW, pH)
            alpr_d = run_alpr(patch_img, pW, pH)

            regex_d = run_regex(lines, pW, pH)
            for ap in alpr_d:
                if not any(iou(ap.bbox, rd.bbox) > 0.4 for rd in regex_d if rd.type == "license_plate"):
                    regex_d.append(ap)
                    
            addr_d = run_address_name(lines, pW, pH)
            ft_d = run_fulltext_scan(lines, pW, pH)
            sig_d = run_signatures(patch_img, pW, pH, lines)
            doc_d = run_doc_classifier(lines, pW, pH)

            yolo_persons = [d for d in yolo_d if d.type == "face"]
            yolo_others  = [d for d in yolo_d if d.type != "face"]
            for yp in yolo_persons:
                if not any(iou(yp.bbox, fd.bbox) > 0.3 for fd in face_d):
                    face_d.append(yp)

            patch_dets = regex_d + addr_d + ft_d + face_d + qr_d + yolo_others + sig_d + doc_d + nsfw_d
            
            # Convert patch percentage coordinates to global percentage coordinates
            scale_x = pW / W
            scale_y = pH / H
            off_x_pct = (off_x_px / W) * 100.0
            off_y_pct = (off_y_px / H) * 100.0
            
            for d in patch_dets:
                d.bbox.x0 = d.bbox.x0 * scale_x + off_x_pct
                d.bbox.x1 = d.bbox.x1 * scale_x + off_x_pct
                d.bbox.y0 = d.bbox.y0 * scale_y + off_y_pct
                d.bbox.y1 = d.bbox.y1 * scale_y + off_y_pct
                if d.confidence >= 70.0 or d.type in ("weapon", "nsfw"):
                    d.redacted = True

            patch_words = []
            for ln in lines:
                box, (t, c) = ln
                try:
                    xs = [float(p[0]) for p in box]
                    ys = [float(p[1]) for p in box]
                    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
                    
                    x0_pct = max(0.0, min(100.0, (x0 / pW) * 100.0)) * scale_x + off_x_pct
                    x1_pct = max(0.0, min(100.0, (x1 / pW) * 100.0)) * scale_x + off_x_pct
                    y0_pct = max(0.0, min(100.0, (y0 / pH) * 100.0)) * scale_y + off_y_pct
                    y1_pct = max(0.0, min(100.0, (y1 / pH) * 100.0)) * scale_y + off_y_pct
                    
                    patch_words.append(OCRWord(
                        text=str(t), confidence=float(c),
                        bbox=BoundingBox(x0=x0_pct, y0=y0_pct, x1=x1_pct, y1=y1_pct)
                    ))
                except:
                    pass
                    
            return patch_dets, patch_words, lines

        all_dets = []
        words_out = []
        total_lines = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(process_patch, patches))
            
        for pdets, pwords, plines in results:
            all_dets.extend(pdets)
            words_out.extend(pwords)
            total_lines.extend(plines)
            
        full_text = " ".join(str(ln[1][0]) for ln in total_lines if ln[1][0])
        ocr_ms = int((time.time() - t_start) * 1000)

        # -- Merge & NMS Global ----------------------------------------------------
        face_dets   = [d for d in all_dets if d.type == "face"]
        weapon_dets = [d for d in all_dets if d.type == "weapon"]
        nsfw_dets   = [d for d in all_dets if d.type == "nsfw"]
        text_dets   = [d for d in all_dets if d.type not in ("face", "weapon", "nsfw")]
    
        merged = (
            nms(face_dets, thr=0.35)
            + weapon_dets
            + nsfw_dets
            + nms(text_dets, thr=0.7)
        )
    
        merged = [
            d for d in merged
            if (d.bbox.x1 - d.bbox.x0) > 0
            and (d.bbox.y1 - d.bbox.y0) > 0
            and d.type != "vehicle"
        ]
    
        diagnostics["Final"] = f"✓ {len(merged)} total detections"
        diagnostics["Tiling"] = "Active (4 Quadrants)"
    
        # -- Privacy Score ---------------------------------------------------------
        base_score = 100
        for d in merged:
            if d.type == "nsfw":
                base_score -= 35
            elif d.type in ("face", "aadhaar", "pan"):
                base_score -= 20
            elif d.type in ("phone", "email"):
                base_score -= 15
            elif d.type == "address":
                base_score -= 18
            elif d.type == "weapon":
                base_score -= 25
            elif d.type == "license_plate":
                base_score -= 12
            elif d.type == "signature":
                base_score -= 10
            elif d.type.startswith("document_"):
                base_score -= 8
            else:
                base_score -= 5
        privacy_score = max(0, min(100, base_score))
    
        # -- Metrics ---------------------------------------------------------------
        ms = int((time.time() - t0) * 1000)
        total_area = W * H
        redacted_area = sum(
            ((d.bbox.x1 - d.bbox.x0) / 100.0 * W) * ((d.bbox.y1 - d.bbox.y0) / 100.0 * H)
            for d in merged if d.redacted
        )
        coverage_pct = min(100.0, (redacted_area / total_area) * 100.0) if total_area > 0 else 0.0
        mem_mb = psutil.Process().memory_info().rss / (1024 * 1024)
    
        metrics = SystemMetrics(
            ocr_latency_ms=ocr_ms,
            total_latency_ms=ms,
            redaction_coverage_pct=round(coverage_pct, 2),
            memory_usage_mb=round(mem_mb, 2)
        )
    
        print(f"[Scan] 4-WAY DONE {ms}ms | {W}x{H} | merged={len(merged)} | privacy={privacy_score}")
    
        return ScanResponse(
            detections=merged,
            words=words_out,
            fullText=full_text.strip(),
            processingTime=ms,
            aiDescription="",
            privacyScore=privacy_score,
            metrics=metrics,
            diagnostics=diagnostics
        )\n"""

new_lines = lines[:start_idx] + [NEW_BLOCK] + lines[end_idx:]
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Successfully patched main.py')
