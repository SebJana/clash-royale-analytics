export type ChartDataset = {
  data: number[];
  label: string;
  color: string;
};

export type ChartConfig = {
  datasets: ChartDataset[];
  labels: string[];
  title: string;
  labelColor: string;
  xAxisTitle: string;
  yAxisTitle: string;
  showLegend?: boolean;
};
