import type { ChartConfig } from "../../types/chart";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Filler,
} from "chart.js";
import { Line } from "react-chartjs-2";

export function LineChart({
  config,
  className,
}: Readonly<{
  config: ChartConfig;
  className?: string;
}>) {
  ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Filler
  );

  // Create gradient for better visual appeal
  const createGradient = (ctx: CanvasRenderingContext2D, color: string) => {
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    // Convert hex to rgba format for proper gradient colors
    const hexToRgba = (hex: string, alpha: number) => {
      const r = parseInt(hex.slice(1, 3), 16);
      const g = parseInt(hex.slice(3, 5), 16);
      const b = parseInt(hex.slice(5, 7), 16);
      return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    };

    gradient.addColorStop(0, hexToRgba(color, 0.25)); // 25% opacity at top
    gradient.addColorStop(1, hexToRgba(color, 0.03)); // 3% opacity at bottom
    return gradient;
  };

  const data = {
    labels: config.labels,
    datasets: [
      {
        label: config.yAxisTitle,
        data: config.data,
        backgroundColor: (context: {
          chart: { ctx: CanvasRenderingContext2D };
        }) => {
          const chart = context.chart;
          const { ctx } = chart;
          return createGradient(ctx, config.chartColor);
        },
        borderColor: config.chartColor,
        borderWidth: 3,
        fill: true,
        tension: 0.2, // Smoother curves
        pointRadius: 6,
        pointHoverRadius: 8,
        pointBackgroundColor: config.chartColor,
        pointBorderColor: "#ffffff",
        pointBorderWidth: 2,
        pointHoverBackgroundColor: config.chartColor,
        pointHoverBorderColor: "#ffffff",
        pointHoverBorderWidth: 3,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      intersect: false,
      mode: "index" as const,
    },
    plugins: {
      legend: {
        display: false,
      },
      title: {
        display: true,
        text: config.title,
        color: config.labelColor,
        font: {
          size: 18,
          weight: "bold" as const,
        },
        padding: {
          top: 10,
          bottom: 30,
        },
      },
      tooltip: {
        backgroundColor: "rgba(0, 0, 0, 0.8)",
        titleColor: "#ffffff",
        bodyColor: "#ffffff",
        borderColor: config.chartColor,
        borderWidth: 1,
        cornerRadius: 8,
        displayColors: true,
        caretPadding: 10,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: config.yAxisTitle,
          color: config.labelColor,
          font: {
            size: 14,
            weight: "normal" as const,
          },
        },
        ticks: {
          color: config.labelColor,
          font: {
            size: 12,
          },
          padding: 10,
        },
        grid: {
          color: "rgba(255, 255, 255, 0.1)",
          drawBorder: false,
        },
      },
      x: {
        title: {
          display: true,
          text: config.xAxisTitle,
          color: config.labelColor,
          font: {
            size: 14,
            weight: "normal" as const,
          },
        },
        ticks: {
          color: config.labelColor,
          font: {
            size: 12,
          },
          maxRotation: 45,
          padding: 10,
        },
        grid: {
          color: "rgba(255, 255, 255, 0.1)",
          drawBorder: false,
        },
      },
    },
  };

  // Generate stable unique key to prevent canvas reuse issues
  const chartKey = `${config.title.replace(
    " ",
    ""
  )}-${config.yAxisTitle.replace(" ", "")}-${config.data[0]}`;

  return (
    <div className={className}>
      <Line key={chartKey} data={data} options={options} />
    </div>
  );
}
