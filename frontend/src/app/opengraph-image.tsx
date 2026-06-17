import { ImageResponse } from "next/og";

export const alt = "ThreadSpace — build in public for the open-source world";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Dynamically rendered social preview image (og:image / twitter:image).
export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          justifyContent: "center",
          backgroundColor: "#0a0a0f",
          backgroundImage:
            "radial-gradient(circle at 75% 20%, rgba(124,92,255,0.35), transparent 55%)",
          padding: "90px",
          fontFamily: "monospace",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", marginBottom: "36px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: "104px",
              height: "104px",
              borderRadius: "24px",
              backgroundColor: "#7c5cff",
              color: "#ffffff",
              fontSize: "46px",
              fontWeight: 700,
              marginRight: "28px",
            }}
          >
            &lt;/&gt;
          </div>
          <div style={{ display: "flex", color: "#ffffff", fontSize: "68px", fontWeight: 700 }}>
            ThreadSpace
          </div>
        </div>
        <div style={{ display: "flex", color: "#b6b6c6", fontSize: "38px", maxWidth: "940px" }}>
          Build in public for the open-source world.
        </div>
      </div>
    ),
    { ...size },
  );
}
