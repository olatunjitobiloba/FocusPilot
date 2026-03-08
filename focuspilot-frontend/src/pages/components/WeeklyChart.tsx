// src/components/WeeklyChart.tsx
import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '../../api/client';

function WeeklyChart() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadWeeklyData();
  }, []);

  const loadWeeklyData = async () => {
    try {
      const response = await api.get('/stats/weekly');
      const weeklyData = response.data;

      // Transform data for chart
      const chartData = Object.entries(weeklyData.daily_breakdown).map(([date, stats]: [string, any]) => ({
        date: new Date(date).toLocaleDateString('en-US', { weekday: 'short' }),
        hours: Math.round((stats.minutes / 60) * 10) / 10,
        sessions: stats.sessions
      }));

      // Sort by date
      chartData.sort((a, b) => {
        const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        return days.indexOf(a.date) - days.indexOf(b.date);
      });

      setData(chartData);
    } catch (error) {
      console.error('Error loading weekly data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading chart...</div>;
  }

  return (
    <div>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis label={{ value: 'Hours', angle: -90, position: 'insideLeft' }} />
          <Tooltip 
            formatter={(value: number | undefined) => value !== undefined ? [`${value}h`, 'Focus Time'] : null}
            labelFormatter={(label) => `Day: ${label}`}
          />
          <Bar dataKey="hours" fill="#667eea" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default WeeklyChart;
