import React, { useEffect, useState } from 'react';
import Navbar from '../components/Navbar';
import { executionAPI } from '../api/client';
import { AgentAction, BlockState } from '../types/execution';

const ACTION_CONFIG: Record<string, {
	icon: string; color: string; label: string
}> = {
	block_sites: { icon: '🔒', color: 'text-red-600', label: 'Sites Blocked' },
	unblock_sites: { icon: '🔓', color: 'text-green-600', label: 'Sites Unblocked' },
	start_session: { icon: '▶️', color: 'text-blue-600', label: 'Session Started' },
	end_session: { icon: '⏹️', color: 'text-orange-600', label: 'Session Ended' },
	send_nudge: { icon: '📢', color: 'text-purple-600', label: 'Nudge Sent' },
	schedule_nudge: { icon: '⏰', color: 'text-yellow-600', label: 'Nudge Scheduled' },
	activate_focus_mode: { icon: '🎯', color: 'text-indigo-600', label: 'Focus Mode' }
};

const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
	completed: { color: 'bg-green-100  text-green-700', label: 'Completed' },
	failed: { color: 'bg-red-100    text-red-700', label: 'Failed' },
	undone: { color: 'bg-gray-100   text-gray-600', label: 'Undone' },
	executing: { color: 'bg-blue-100   text-blue-700', label: 'Running' },
	pending: { color: 'bg-yellow-100 text-yellow-700', label: 'Pending' }
};

function ExecutionLog() {
	const [actions, setActions] = useState<AgentAction[]>([]);
	const [blockState, setBlockState] = useState<BlockState | null>(null);
	const [loading, setLoading] = useState(true);
	const [undoing, setUndoing] = useState<string | null>(null);

	useEffect(() => {
		loadData();
		const interval = setInterval(loadData, 30_000);
		return () => clearInterval(interval);
	}, []);

	const loadData = async () => {
		try {
			const [actionsRes, blockRes] = await Promise.all([
				executionAPI.getActions(30),
				executionAPI.getBlockState()
			]);
			setActions(actionsRes.data.actions || []);
			setBlockState(blockRes.data);
		} catch (error) {
			console.error('Error loading execution data:', error);
		} finally {
			setLoading(false);
		}
	};

	const handleUndo = async (actionId: string) => {
		setUndoing(actionId);
		try {
			await executionAPI.undoAction(actionId);
			await loadData();
		} catch (error: any) {
			alert(error.response?.data?.detail || 'Could not undo action');
		} finally {
			setUndoing(null);
		}
	};

	const handleManualBlock = async () => {
		try {
			await executionAPI.manualBlock(25);
			await loadData();
		} catch (error) {
			alert('Could not activate block');
		}
	};

	const handleManualUnblock = async () => {
		try {
			await executionAPI.manualUnblock();
			await loadData();
		} catch (error) {
			alert('Could not unblock sites');
		}
	};

	if (loading) {
		return (
			<div className="min-h-screen bg-gray-100">
				<Navbar />
				<div className="flex items-center justify-center h-64">
					<p className="text-gray-500 text-xl animate-pulse">
						Loading execution log...
					</p>
				</div>
			</div>
		);
	}

	const completedCount = actions.filter((a) => a.status === 'completed').length;
	const failedCount = actions.filter((a) => a.status === 'failed').length;
	const undoneCount = actions.filter((a) => a.status === 'undone').length;

	return (
		<div className="min-h-screen bg-gray-100">
			<Navbar />

			<main className="max-w-5xl mx-auto px-4 py-8">
				{/* Header */}
				<div className="flex justify-between items-center mb-8">
					<div>
						<h1 className="text-3xl font-bold text-gray-900">
							⚡ Execution Log
						</h1>
						<p className="text-gray-600 mt-1">
							Every autonomous action your agent has taken
						</p>
					</div>

					{/* Manual controls */}
					<div className="flex gap-3">
						{blockState?.is_blocked ? (
							<button
								onClick={handleManualUnblock}
								className="px-4 py-2 bg-green-600 text-white rounded-lg
									font-medium hover:bg-green-700 transition text-sm"
							>
								🔓 Unblock Sites
							</button>
						) : (
							<button
								onClick={handleManualBlock}
								className="px-4 py-2 bg-red-600 text-white rounded-lg
									font-medium hover:bg-red-700 transition text-sm"
							>
								🔒 Block Sites (25 min)
							</button>
						)}
					</div>
				</div>

				{/* Block state banner */}
				{blockState?.is_blocked && (
					<div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
						<div className="flex items-center justify-between">
							<div className="flex items-center gap-3">
								<span className="text-2xl">🔒</span>
								<div>
									<p className="font-semibold text-red-800">
										Focus Mode Active
									</p>
									<p className="text-sm text-red-600">
										{blockState.blocked_domains?.length || 0} sites blocked
										{blockState.unblock_at && (
											` · Unblocks at ${new Date(blockState.unblock_at).toLocaleTimeString()}`
										)}
									</p>
								</div>
							</div>
							<button
								onClick={handleManualUnblock}
								className="text-sm text-red-600 hover:underline font-medium"
							>
								Unblock Now
							</button>
						</div>
					</div>
				)}

				{/* Stats row */}
				<div className="grid grid-cols-3 gap-4 mb-8">
					<div className="bg-white rounded-xl shadow p-5 text-center">
						<p className="text-3xl font-bold text-green-600">
							{completedCount}
						</p>
						<p className="text-sm text-gray-500 mt-1">Completed</p>
					</div>
					<div className="bg-white rounded-xl shadow p-5 text-center">
						<p className="text-3xl font-bold text-gray-500">
							{undoneCount}
						</p>
						<p className="text-sm text-gray-500 mt-1">Undone</p>
					</div>
					<div className="bg-white rounded-xl shadow p-5 text-center">
						<p className="text-3xl font-bold text-red-500">
							{failedCount}
						</p>
						<p className="text-sm text-gray-500 mt-1">Failed</p>
					</div>
				</div>

				{/* Actions list */}
				{actions.length === 0 ? (
					<div className="text-center py-20">
						<span className="text-6xl block mb-4">⚡</span>
						<p className="text-gray-500 text-xl">No actions yet.</p>
						<p className="text-gray-400 text-sm mt-2">
							The agent will take autonomous actions when it detects
							procrastination.
						</p>
					</div>
				) : (
					<div className="space-y-3">
						{actions.map((action) => (
							<ActionCard
								key={action.id}
								action={action}
								onUndo={handleUndo}
								undoing={undoing === action.id}
							/>
						))}
					</div>
				)}
			</main>
		</div>
	);
}

function ActionCard({
	action,
	onUndo,
	undoing
}: {
	action: AgentAction;
	onUndo: (id: string) => void;
	undoing: boolean;
}) {
	const actionCfg = ACTION_CONFIG[action.action_type] || {
		icon: '⚡', color: 'text-gray-600', label: action.action_type
	};
	const statusCfg = STATUS_CONFIG[action.status] || STATUS_CONFIG.pending;

	return (
		<div className="bg-white rounded-xl shadow-sm p-5">
			<div className="flex items-start justify-between">
				{/* Left: icon + info */}
				<div className="flex items-start gap-4">
					<span className="text-3xl mt-0.5">{actionCfg.icon}</span>
					<div>
						<div className="flex items-center gap-2 mb-1">
							<p className={`font-bold text-base ${actionCfg.color}`}>
								{actionCfg.label}
							</p>
							<span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusCfg.color}`}>
								{statusCfg.label}
							</span>
						</div>

						<p className="text-sm text-gray-600 mb-1">
							{action.trigger_reason}
						</p>

						{/* Action details */}
						{action.action_data && Object.keys(action.action_data).length > 0 && (
							<div className="flex flex-wrap gap-2 mt-2">
								{action.action_type === 'block_sites' && (
									<span className="text-xs bg-red-50 text-red-600 px-2 py-0.5 rounded">
										{action.action_data.domains?.length || 0} domains blocked
									</span>
								)}
								{action.action_data.duration_minutes && (
									<span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded">
										{action.action_data.duration_minutes} minutes
									</span>
								)}
								{action.risk_score_at_trigger != null && (
									<span className="text-xs bg-orange-50 text-orange-600 px-2 py-0.5 rounded">
										Risk: {Math.round(action.risk_score_at_trigger * 100)}%
									</span>
								)}
							</div>
						)}

						<p className="text-xs text-gray-400 mt-2">
							{new Date(action.created_at).toLocaleString()}
							{action.completed_at && (
								` · Completed ${new Date(action.completed_at).toLocaleTimeString()}`
							)}
							{action.undone_at && (
								` · Undone ${new Date(action.undone_at).toLocaleTimeString()}`
							)}
						</p>
					</div>
				</div>

				{/* Right: undo button */}
				{action.is_undoable && action.status === 'completed' && (
					<button
						onClick={() => onUndo(action.id)}
						disabled={undoing}
						className="ml-4 px-3 py-1.5 text-sm border border-gray-300
							text-gray-600 rounded-lg hover:bg-gray-50
							disabled:opacity-50 transition font-medium shrink-0"
					>
						{undoing ? '...' : '↩ Undo'}
					</button>
				)}
			</div>
		</div>
	);
}

export default ExecutionLog;
