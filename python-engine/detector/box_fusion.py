def expand_and_merge(all_raw_dets, W, H, overlap=128, expand_px=8):
    # Map coordinates to global 0-1, apply WBF
    try:
        from ensemble_boxes import weighted_boxes_fusion
    except ImportError:
        return all_raw_dets

    if not all_raw_dets:
        return []

    boxes = []
    scores = []
    labels = []
    
    unique_labels = list(set([d["label"] for d in all_raw_dets]))
    label_map = {l: i for i, l in enumerate(unique_labels)}
    rev_map = {i: l for i, l in enumerate(unique_labels)}

    for d in all_raw_dets:
        bx = d["box"]
        # Expand 8px
        x1 = max(0, bx[0] - expand_px) / W
        y1 = max(0, bx[1] - expand_px) / H
        x2 = min(W, bx[2] + expand_px) / W
        y2 = min(H, bx[3] + expand_px) / H
        boxes.append([x1, y1, x2, y2])
        scores.append(d["score"])
        labels.append(label_map[d["label"]])

    mb, ms, ml = weighted_boxes_fusion([boxes], [scores], [labels], weights=None, iou_thr=0.4, skip_box_thr=0.001)
    
    merged = []
    for b, s, l in zip(mb, ms, ml):
        merged.append({
            "box": b, # 0-1 format
            "score": s,
            "label": rev_map[int(l)]
        })
    return merged
