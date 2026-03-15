// src/components/FeatureImportanceChart.tsx
import React, { useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import { predictionsAPI } from '../api/client';

function FeatureImportanceChart() {
  const [data, setData]       = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [noModel, setNoModel] = useState(false);

  useEffect(() => {
    loadImportance();
  }, []);

  const loadImportance = async () => {
    try {
      const response = await predictionsAPI.getFeatureImportance();
      const top8 = response.data.feature_importance.slice(0, 8);

      setData(top8.map((item: any) => ({
        name:        item.description,
        importance:  item.percentage,
        feature:     item.feature
      })));
    } catch (error: any) {
      if (error.response?.status === 404) {
        setNoModel(true);
      }
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="animate-pulse bg-gray-200 rounded h-48" />;
  }

  if (noModel) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-gray-500">
        <span className="text-4xl mb-3">🤖</span>
        <p className="text-center text-sm">
          Train the AI model to see what drives your procrastination
        </p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ left: 20, right: 20 }}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          type="number"
          unit="%"
          domain={[0, 'auto']}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={160}
          tick={{ fontSize: 11 }}
        />
        <Tooltip
          formatter={(value: number | undefined) => [`${value ?? 0}%`, 'Importance'] as [string, string]}
        />
        <Bar
          dataKey="importance"
          fill="#667eea"
          radius={[0, 4, 4, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

export default FeatureImportanceChart;
