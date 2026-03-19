// src/components/DistractionsChart.tsx
import React, { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { api } from '../../api/client';
import { CHART_GREEN } from '../../utils/greenPalette';

function DistractionsChart() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDistractions();
  }, []);

  const loadDistractions = async () => {
    try {
      const response = await api.get('/analytics/distractions?days=7');
      const distractions = response.data.top_distractions.slice(0, 5); // Top 5

      const chartData = distractions.map((d: any) => ({
        name: d.domain,
        value: d.total_minutes,
        hours: d.total_hours
      }));

      setData(chartData);
    } catch (error) {
      console.error('Error loading distractions:', error);
    } finally {
      setLoading(false);
    }
  };

  const COLORS = CHART_GREEN.series;

  if (loading) {
    return <div className="text-center py-8">Loading chart...</div>;
  }

  if (data.length === 0) {
    return (
      <div className="text-center py-8 text-gray-600">
        No distractions tracked yet. Start a focus session to see data!
      </div>
    );
  }

  return (
    <div>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percent }) => `${name} (${((percent ?? 0) * 100).toFixed(0)}%)`}
            outerRadius={80}
            fill={CHART_GREEN.bar}
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(value) => value !== undefined ? `${Math.round(Number(value))} minutes` : '0 minutes'} />
        </PieChart>
      </ResponsiveContainer>

      {/* List view */}
      <div className="mt-4 space-y-2">
        {data.map((item, index) => (
          <div key={index} className="flex justify-between items-center">
            <div className="flex items-center">
              <div 
                className="w-4 h-4 rounded-full mr-2"
                style={{ backgroundColor: COLORS[index % COLORS.length] }}
              />
              <span className="text-sm text-gray-700">{item.name}</span>
            </div>
            <span className="text-sm font-semibold text-gray-900">
              {item.hours}h
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default DistractionsChart;
