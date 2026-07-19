import { useState } from "react";

interface EntityImageProps {
  src: string;
  alt: string;
  width?: number;
  height?: number;
  eager?: boolean;
}

export function EntityImage({
  src,
  alt,
  width,
  height,
  eager = false,
}: EntityImageProps) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <div className="entity-image-fallback" role="img" aria-label={alt}>
        Изображение временно недоступно
      </div>
    );
  }
  return (
    <img
      src={src}
      alt={alt}
      width={width}
      height={height}
      loading={eager ? "eager" : "lazy"}
      fetchPriority={eager ? "high" : "auto"}
      onError={() => {
        setFailed(true);
      }}
    />
  );
}
