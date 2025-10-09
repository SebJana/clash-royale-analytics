import type { ChartConfig } from "../../types/chart";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Line } from "react-chartjs-2";

export function LineChart({ config }: Readonly<{ config: ChartConfig }>) {
  ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend
  );

  const data = {
    labels: config.labels,
    datasets: [
      {
        label: config.yAxisTitle,
        data: config.data,
        backgroundColor: config.chartColor,
        borderColor: config.chartColor,
        borderWidth: 1.5,
        fill: true,
        tension: 0.3,
        pointRadius: 5,
        pointHoverRadius: 7,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: "top" as const,
        labels: {
          color: config.labelColor,
        },
      },
      title: {
        display: true,
        text: config.title,
        color: config.labelColor,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: config.yAxisTitle,
          color: config.labelColor,
        },
        ticks: {
          color: config.labelColor,
        },
      },
      x: {
        title: {
          display: true,
          text: config.xAxisTitle,
          color: config.labelColor,
        },
        ticks: {
          color: config.labelColor,
        },
      },
    },
  };

  return <Line data={data} options={options} />;
}
