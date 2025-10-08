import { useEffect, useState } from "react";
import { ChevronUp } from "lucide-react";
import "./scrollToTop.css";

export function ScrollToTopButton() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const toggleVisible = () => {
      const scrolled = window.scrollY;
      setVisible(scrolled > 2000); // show after 2000px scroll
    };

    window.addEventListener("scroll", toggleVisible);
    return () => window.removeEventListener("scroll", toggleVisible);
  }, []);

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <button
      onClick={scrollToTop}
      className={`scroll-to-top-button ${visible ? "visible" : ""}`}
    >
      <ChevronUp size={30} />
    </button>
  );
}
