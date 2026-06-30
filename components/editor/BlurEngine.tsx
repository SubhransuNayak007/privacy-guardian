import React, { useRef, useEffect } from 'react';
import Konva from 'konva';
import { Image as KonvaImage, Rect, Circle, Group, Line } from 'react-konva';
import { EditorLayer } from '@/lib/editor-store';

interface BlurStrategyProps {
  layer: EditorLayer;
  image: HTMLImageElement | undefined;
}

const BrushGroup = ({ layer, image, children }: any) => {
  const groupRef = useRef<any>(null);

  useEffect(() => {
    if (groupRef.current && image && image.width > 0 && image.height > 0) {
      try {
        groupRef.current.cache();
      } catch (e) {
        console.warn('BrushGroup cache skipped:', e);
      }
    }
  }, [layer.points, layer.blurStrength, layer.brushSize, layer.opacity, image, children]);

  const baseScale = image ? Math.max(image.width, image.height) / 1000 : 1;

  return (
    <Group ref={groupRef} opacity={layer.opacity}>
      <Line
        points={layer.points || []}
        stroke="black"
        strokeWidth={(layer.brushSize || 20) * baseScale}
        tension={0.5}
        lineCap="round"
        lineJoin="round"
      />
      <Group globalCompositeOperation="source-in">
        {children}
      </Group>
    </Group>
  );
};

const GaussianStrategy = ({ layer, image }: BlurStrategyProps) => {
  const imageRef = useRef<any>(null);

  useEffect(() => {
    if (imageRef.current && image && image.width > 0 && image.height > 0) {
      try {
        imageRef.current.cache();
      } catch (e) {
        console.warn('Gaussian cache skipped:', e);
      }
    }
  }, [layer.blurStrength, image, layer.x, layer.y, layer.width, layer.height, layer.points]);

  const baseScale = image ? Math.max(image.width, image.height) / 1000 : 1;
  const blurRadius = Math.round((layer.blurStrength / 100) * 80) * baseScale;

  if (layer.type === 'brush') {
    return (
      <BrushGroup layer={layer} image={image}>
        <KonvaImage
          ref={imageRef}
          image={image}
          filters={[Konva.Filters.Blur]}
          blurRadius={blurRadius}
        />
      </BrushGroup>
    );
  }

  return (
    <Group opacity={layer.opacity}>
      <Group clipFunc={(ctx) => {
        // We use clipFunc to restrict the filtered image to the shape's bounds
        ctx.beginPath();
        if (layer.type === 'rect') {
          ctx.rect(layer.x, layer.y, layer.width || 0, layer.height || 0);
        } else if (layer.type === 'circle') {
          ctx.arc(layer.x, layer.y, layer.radius || 0, 0, Math.PI * 2, false);
        }
        ctx.closePath();
      }}>
        <KonvaImage
          ref={imageRef}
          image={image}
          crop={{
            x: layer.type === 'circle' ? layer.x - (layer.radius || 0) : layer.x,
            y: layer.type === 'circle' ? layer.y - (layer.radius || 0) : layer.y,
            width: layer.type === 'circle' ? (layer.radius || 0) * 2 : (layer.width || 0),
            height: layer.type === 'circle' ? (layer.radius || 0) * 2 : (layer.height || 0),
          }}
          x={layer.type === 'circle' ? layer.x - (layer.radius || 0) : layer.x}
          y={layer.type === 'circle' ? layer.y - (layer.radius || 0) : layer.y}
          width={layer.type === 'circle' ? (layer.radius || 0) * 2 : (layer.width || 0)}
          height={layer.type === 'circle' ? (layer.radius || 0) * 2 : (layer.height || 0)}
          filters={[Konva.Filters.Blur]}
          blurRadius={blurRadius}
        />
      </Group>
    </Group>
  );
};

const PixelateStrategy = ({ layer, image }: BlurStrategyProps) => {
  const imageRef = useRef<any>(null);

  useEffect(() => {
    if (imageRef.current && image && image.width > 0 && image.height > 0) {
      try {
        imageRef.current.cache();
      } catch (e) {
        console.warn('Pixelate cache skipped:', e);
      }
    }
  }, [layer.blurStrength, image, layer.x, layer.y, layer.width, layer.height, layer.points]);

  const baseScale = image ? Math.max(image.width, image.height) / 1000 : 1;
  const pixelSize = Math.max(1, Math.round((layer.blurStrength / 100) * 40) * baseScale);

  if (layer.type === 'brush') {
    return (
      <BrushGroup layer={layer} image={image}>
        <KonvaImage
          ref={imageRef}
          image={image}
          filters={[Konva.Filters.Pixelate]}
          pixelSize={pixelSize}
        />
      </BrushGroup>
    );
  }

  return (
    <Group opacity={layer.opacity}>
      <Group clipFunc={(ctx) => {
        ctx.beginPath();
        if (layer.type === 'rect') {
          ctx.rect(layer.x, layer.y, layer.width || 0, layer.height || 0);
        } else if (layer.type === 'circle') {
          ctx.arc(layer.x, layer.y, layer.radius || 0, 0, Math.PI * 2, false);
        }
        ctx.closePath();
      }}>
        <KonvaImage
          ref={imageRef}
          image={image}
          crop={{
            x: layer.type === 'circle' ? layer.x - (layer.radius || 0) : layer.x,
            y: layer.type === 'circle' ? layer.y - (layer.radius || 0) : layer.y,
            width: layer.type === 'circle' ? (layer.radius || 0) * 2 : (layer.width || 0),
            height: layer.type === 'circle' ? (layer.radius || 0) * 2 : (layer.height || 0),
          }}
          x={layer.type === 'circle' ? layer.x - (layer.radius || 0) : layer.x}
          y={layer.type === 'circle' ? layer.y - (layer.radius || 0) : layer.y}
          width={layer.type === 'circle' ? (layer.radius || 0) * 2 : (layer.width || 0)}
          height={layer.type === 'circle' ? (layer.radius || 0) * 2 : (layer.height || 0)}
          filters={[Konva.Filters.Pixelate]}
          pixelSize={pixelSize}
        />
      </Group>
    </Group>
  );
};

const SolidColorStrategy = ({ layer, color, image }: { layer: EditorLayer, color: string, image: HTMLImageElement | undefined }) => {
  const baseScale = image ? Math.max(image.width, image.height) / 1000 : 1;
  const imgW = image?.width || 1;
  const imgH = image?.height || 1;
  
  if (layer.type === 'polygon' && layer.polygon) {
    const pts = layer.polygon.map((val, i) => (val / 100) * (i % 2 === 0 ? imgW : imgH));
    return (
      <Line
        points={pts}
        closed={true}
        fill={color}
        opacity={layer.opacity}
      />
    );
  }
  if (layer.type === 'rect') {
    return (
      <Rect
        x={layer.x}
        y={layer.y}
        width={layer.width}
        height={layer.height}
        rotation={layer.rotation || 0}
        cornerRadius={layer.cornerRadius || 0}
        fill={color}
        opacity={layer.opacity}
      />
    );
  }
  if (layer.type === 'circle') {
    return (
      <Circle
        x={layer.x}
        y={layer.y}
        radius={layer.radius}
        rotation={layer.rotation || 0}
        fill={color}
        opacity={layer.opacity}
      />
    );
  }
  if (layer.type === 'brush') {
    return (
      <Line
        points={layer.points || []}
        stroke={color}
        strokeWidth={(layer.brushSize || 20) * baseScale}
        opacity={layer.opacity}
        tension={0.5}
        lineCap="round"
        lineJoin="round"
      />
    );
  }
  return null;
};

// Wrapper component that ensures cache() is called for filters
const FilteredImage = ({ filters, blurRadius, pixelSize, noise, image, crop, pos }: any) => {
  const imageRef = useRef<any>(null);
  useEffect(() => {
    if (imageRef.current && image && image.width > 0 && image.height > 0) {
      try {
        imageRef.current.cache();
      } catch (e) {
        console.warn('Filter cache skipped:', e);
      }
    }
  }, [filters, blurRadius, pixelSize, noise, pos.x, pos.y, pos.width, pos.height, crop?.x, crop?.y, image]);

  return (
    <KonvaImage
      ref={imageRef}
      image={image}
      crop={crop}
      x={pos.x}
      y={pos.y}
      width={pos.width}
      height={pos.height}
      filters={filters}
      blurRadius={blurRadius}
      pixelSize={pixelSize}
      noise={noise}
    />
  );
};

const FullImage = ({ filters, blurRadius, pixelSize, noise, image }: any) => {
  const imageRef = useRef<any>(null);
  useEffect(() => {
    if (imageRef.current && image && image.width > 0 && image.height > 0) {
      try {
        imageRef.current.cache();
      } catch (e) {
        console.warn('Filter cache skipped:', e);
      }
    }
  }, [filters, blurRadius, pixelSize, noise, image]);

  return (
    <KonvaImage
      ref={imageRef}
      image={image}
      filters={filters}
      blurRadius={blurRadius}
      pixelSize={pixelSize}
      noise={noise}
    />
  );
};

export const BlurEngine = ({ layer, image }: BlurStrategyProps) => {
  if (!layer.visible) return null;
  const getClipFunc = () => {
    return (ctx: any) => {
      const imgW = image?.width || 1;
      const imgH = image?.height || 1;
      
      ctx.beginPath();
      if (layer.type === 'polygon' && layer.polygon) {
        const pts = layer.polygon.map((val, i) => (val / 100) * (i % 2 === 0 ? imgW : imgH));
        if (pts.length >= 2) {
            ctx.moveTo(pts[0], pts[1]);
            for(let i=2; i<pts.length; i+=2) {
                ctx.lineTo(pts[i], pts[i+1]);
            }
            ctx.closePath();
        }
      } else if (layer.type === 'rect') {
        ctx.rect(layer.x, layer.y, layer.width || 0, layer.height || 0);
      } else if (layer.type === 'circle') {
        ctx.arc(layer.x, layer.y, layer.radius || 0, 0, Math.PI * 2, false);
      }
      if (layer.type !== 'polygon') {
         ctx.closePath();
      }
    };
  };

  const getCrop = () => {
    if (layer.type === 'polygon') return undefined; // Crop isn't reliable for custom polygons, we rely purely on clipFunc
    return {
      x: layer.type === 'circle' ? layer.x - (layer.radius || 0) : layer.x,
      y: layer.type === 'circle' ? layer.y - (layer.radius || 0) : layer.y,
      width: layer.type === 'circle' ? (layer.radius || 0) * 2 : (layer.width || 0),
      height: layer.type === 'circle' ? (layer.radius || 0) * 2 : (layer.height || 0),
    };
  };
  
  const getPos = () => {
    if (layer.type === 'polygon') return { x: 0, y: 0, width: image?.width || 0, height: image?.height || 0 };
    return {
      x: layer.type === 'circle' ? layer.x - (layer.radius || 0) : layer.x,
      y: layer.type === 'circle' ? layer.y - (layer.radius || 0) : layer.y,
      width: layer.type === 'circle' ? (layer.radius || 0) * 2 : (layer.width || 0),
      height: layer.type === 'circle' ? (layer.radius || 0) * 2 : (layer.height || 0),
    };
  };

  const pos = getPos();
  const crop = getCrop();
  const baseScale = image ? Math.max(image.width, image.height) / 1000 : 1;

  switch (layer.blurType) {
    case 'gaussian':
      if (layer.type === 'brush') {
          return (
            <BrushGroup layer={layer} image={image}>
              <FullImage image={image} filters={[Konva.Filters.Blur]} blurRadius={Math.round((layer.blurStrength / 100) * 80) * baseScale} />
            </BrushGroup>
          );
      }
      return (
        <Group opacity={layer.opacity}>
          <Group clipFunc={getClipFunc()}>
            <FilteredImage image={image} crop={crop} pos={pos} filters={[Konva.Filters.Blur]} blurRadius={Math.round((layer.blurStrength / 100) * 80) * baseScale} />
          </Group>
        </Group>
      );
      
    case 'pixelate':
    case 'mosaic':
      if (layer.type === 'brush') {
          return (
            <BrushGroup layer={layer} image={image}>
              <FullImage image={image} filters={[Konva.Filters.Pixelate]} pixelSize={Math.max(1, Math.round((layer.blurStrength / 100) * 40) * baseScale)} />
            </BrushGroup>
          );
      }
      return (
        <Group opacity={layer.opacity}>
          <Group clipFunc={getClipFunc()}>
            <FilteredImage image={image} crop={crop} pos={pos} filters={[Konva.Filters.Pixelate]} pixelSize={Math.max(1, Math.round((layer.blurStrength / 100) * 40) * baseScale)} />
          </Group>
        </Group>
      );
      
    case 'motion':
      // Motion blur simulated with Noise + Blur
      if (layer.type === 'brush') {
          return (
            <BrushGroup layer={layer} image={image}>
              <FullImage image={image} filters={[Konva.Filters.Noise, Konva.Filters.Blur]} noise={layer.blurStrength / 50} blurRadius={Math.round((layer.blurStrength / 100) * 40) * baseScale} />
            </BrushGroup>
          );
      }
      return (
        <Group opacity={layer.opacity}>
          <Group clipFunc={getClipFunc()}>
            <FilteredImage image={image} crop={crop} pos={pos} filters={[Konva.Filters.Noise, Konva.Filters.Blur]} noise={layer.blurStrength / 50} blurRadius={Math.round((layer.blurStrength / 100) * 40) * baseScale} />
          </Group>
        </Group>
      );
      
    case 'context':
      // Context blur simulated with heavy pixelate + heavy blur (generative fill placeholder)
      if (layer.type === 'brush') {
          return (
            <BrushGroup layer={layer} image={image}>
              <FullImage image={image} filters={[Konva.Filters.Pixelate, Konva.Filters.Blur]} pixelSize={40} blurRadius={40} />
            </BrushGroup>
          );
      }
      return (
        <Group opacity={layer.opacity}>
          <Group clipFunc={getClipFunc()}>
            <FilteredImage image={image} crop={crop} pos={pos} filters={[Konva.Filters.Pixelate, Konva.Filters.Blur]} pixelSize={40} blurRadius={40} />
          </Group>
        </Group>
      );

    case 'black': return <SolidColorStrategy layer={layer} image={image} color="#000000" />;
    case 'white': return <SolidColorStrategy layer={layer} image={image} color="#ffffff" />;
    case 'color': return <SolidColorStrategy layer={layer} image={image} color={layer.color || '#ff0000'} />;
    case 'transparent': return <SolidColorStrategy layer={layer} image={image} color="rgba(0,0,0,0.5)" />;
    default: return <SolidColorStrategy layer={layer} image={image} color="#000000" />;
  }
};
