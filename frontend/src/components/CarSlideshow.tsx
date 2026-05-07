import { useEffect, useState } from "react";
import car1 from "@/assets/car-1.jpg";
import car2 from "@/assets/car-2.jpg";
import car3 from "@/assets/car-3.jpg";
import car4 from "@/assets/car-4.jpg";

const slides = [car1, car2, car3, car4];

export function CarSlideshow({ intensity = "full" }: { intensity?: "full" | "soft" }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((p) => (p + 1) % slides.length), 6000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden bg-background">
      {slides.map((src, idx) => (
        <div
          key={idx}
          className="absolute inset-0 transition-opacity duration-[1800ms] ease-out"
          style={{ opacity: idx === i ? 1 : 0 }}
        >
          <img
            src={src}
            alt=""
            className="h-full w-full object-cover"
            style={{ animation: "ken-burns 12s ease-out both" }}
          />
        </div>
      ))}
      <div
        className="absolute inset-0"
        style={{
          background:
            intensity === "full"
              ? "linear-gradient(180deg, oklch(0.1 0.005 30 / 0.15) 0%, oklch(0.1 0.005 30 / 0.45) 60%, oklch(0.08 0.005 30 / 0.75) 100%)"
              : "linear-gradient(180deg, oklch(0.1 0.005 30 / 0.55) 0%, oklch(0.08 0.005 30 / 0.85) 100%)",
        }}
      />
      <div className="absolute inset-0 grid-lines opacity-40" />
      <div
        className="absolute inset-x-0 bottom-0 h-1/2"
        style={{
          background:
            "radial-gradient(ellipse at bottom, oklch(0.68 0.19 38 / 0.18), transparent 70%)",
        }}
      />
    </div>
  );
}
