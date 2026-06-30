import os

def main():
    path = r"D:\rot post\privacy-guardian\python-engine\main.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    start_str = "        # -- 4-WAY TILING ENGINE ----------------------------------------------------"
    end_str = "        # -- Merge & NMS Global ----------------------------------------------------"

    start_idx = content.find(start_str)
    end_idx = content.find(end_str)

    if start_idx == -1 or end_idx == -1:
        print("Could not find replacement boundaries.")
        return

    new_block = """        # -- MODEL-LEVEL CONCURRENCY ENGINE ----------------------------------------------------
        import concurrent.futures
        t_start = time.time()
        
        # Preprocess for OCR
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img_enhanced = cv2.cvtColor(clahe.apply(gray), cv2.COLOR_GRAY2BGR)

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            future_ocr = executor.submit(run_ocr, img_enhanced)
            future_face = executor.submit(run_faces, img, W, H)
            future_qr = executor.submit(run_qr, img, W, H)
            future_yolo = executor.submit(run_yolo, img, W, H)
            future_nsfw = executor.submit(run_nudenet, img, W, H)
            future_alpr = executor.submit(run_alpr, img, W, H)

            lines = future_ocr.result()
            face_d = future_face.result()
            qr_d = future_qr.result()
            yolo_d = future_yolo.result()
            nsfw_d = future_nsfw.result()
            alpr_d = future_alpr.result()

        # Now run dependent text layers (they are fast)
        regex_d = run_regex(lines, W, H)
        for ap in alpr_d:
            if not any(iou(ap.bbox, rd.bbox) > 0.4 for rd in regex_d if rd.type == "license_plate"):
                regex_d.append(ap)
                
        addr_d = run_address_name(lines, W, H)
        ft_d = run_fulltext_scan(lines, W, H)
        sig_d = run_signatures(img, W, H, lines)
        doc_d = run_doc_classifier(lines, W, H)

        yolo_persons = [d for d in yolo_d if d.type == "face"]
        yolo_others  = [d for d in yolo_d if d.type != "face"]
        for yp in yolo_persons:
            if not any(iou(yp.bbox, fd.bbox) > 0.3 for fd in face_d):
                face_d.append(yp)

        all_dets = regex_d + addr_d + ft_d + face_d + qr_d + yolo_others + sig_d + doc_d + nsfw_d
        
        for d in all_dets:
            if d.confidence >= 70.0 or d.type in ("weapon", "nsfw"):
                d.redacted = True

        words_out = []
        for ln in lines:
            box, (t, c) = ln
            try:
                xs = [float(p[0]) for p in box]
                ys = [float(p[1]) for p in box]
                x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
                
                x0_pct = max(0.0, min(100.0, (x0 / W) * 100.0))
                x1_pct = max(0.0, min(100.0, (x1 / W) * 100.0))
                y0_pct = max(0.0, min(100.0, (y0 / H) * 100.0))
                y1_pct = max(0.0, min(100.0, (y1 / H) * 100.0))
                
                words_out.append(OCRWord(
                    text=str(t), confidence=float(c),
                    bbox=BoundingBox(x0=x0_pct, y0=y0_pct, x1=x1_pct, y1=y1_pct)
                ))
            except:
                pass
                
        full_text = " ".join(str(ln[1][0]) for ln in lines if ln[1][0])
        ocr_ms = int((time.time() - t_start) * 1000)

"""

    new_content = content[:start_idx] + new_block + content[end_idx:]

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    
    print("Patch 2 successful.")

if __name__ == "__main__":
    main()
