import React, { useState, useEffect } from 'react';
import {
  ThermometerSnowflake,
  Truck,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Flame,
  Moon,
  Clock,
  Layers,
  ShieldCheck,
  ShieldAlert,
  Hash,
  ChevronRight,
  Plus,
  RefreshCw,
  Info,
} from 'lucide-react';
import { useAuthRole } from '../context/AuthRoleContext';

export default function ColdChainMonitoring() {
  const { authFetch, currentRole, activeRoleConfig } = useAuthRole();
  const [trips, setTrips] = useState([]);
  const [selectedTrip, setSelectedTrip] = useState(null);
  const [loading, setLoading] = useState(false);
  const [runningScenario, setRunningScenario] = useState(null);
  const [simulationResult, setSimulationResult] = useState(null);
  const [availableBatches, setAvailableBatches] = useState([]);

  // Form tạo chuyến xe mới
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newVehicle, setNewVehicle] = useState('REEFER-51D-888.99');
  const [newDriver, setNewDriver] = useState('Nguyễn Văn Tài Xế');
  const [selectedBatchIds, setSelectedBatchIds] = useState([]);
  const [minTemp, setMinTemp] = useState(2.0);
  const [maxTemp, setMaxTemp] = useState(8.0);
  const [createLoading, setCreateLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const isLogisticsOrAdmin = ['carrier', 'logistics', 'transporter', 'admin', 'system_admin'].includes(currentRole);

  useEffect(() => {
    fetchTrips();
    fetchBatches();
  }, [currentRole]);

  const fetchTrips = async () => {
    setLoading(true);
    try {
      const res = await authFetch('/api/v1/cold-chain/trips');
      if (res.ok) {
        const data = await res.json();
        setTrips(data);
        if (data.length > 0 && !selectedTrip) {
          fetchTripDetail(data[0].id);
        } else if (selectedTrip) {
          fetchTripDetail(selectedTrip.id);
        }
      }
    } catch (err) {
      console.error('Lỗi tải danh sách chuyến xe:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchBatches = async () => {
    try {
      const res = await authFetch('/api/v1/batches?limit=50');
      if (res.ok) {
        const data = await res.json();
        setAvailableBatches(data);
        if (data.length > 0 && selectedBatchIds.length === 0) {
          setSelectedBatchIds([data[0].id]);
        }
      }
    } catch (err) {
      console.error('Lỗi tải lô hàng:', err);
    }
  };

  const fetchTripDetail = async (tripId) => {
    try {
      const res = await authFetch(`/api/v1/cold-chain/trips/${tripId}`);
      if (res.ok) {
        const detail = await res.json();
        setSelectedTrip(detail);
      }
    } catch (err) {
      console.error('Lỗi tải chi tiết chuyến:', err);
    }
  };

  const handleCreateTrip = async (e) => {
    e.preventDefault();
    if (selectedBatchIds.length === 0) {
      setErrorMsg('Vui lòng chọn ít nhất 1 lô hàng để vận chuyển.');
      return;
    }
    setCreateLoading(true);
    setErrorMsg(null);
    try {
      const payload = {
        vehicle_code: newVehicle.trim(),
        driver_name: newDriver.trim(),
        batch_ids: selectedBatchIds,
        min_temperature: parseFloat(minTemp),
        max_temperature: parseFloat(maxTemp),
      };
      const res = await authFetch('/api/v1/cold-chain/trips', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Không thể tạo chuyến vận chuyển.');
      }
      const created = await res.json();
      setShowCreateModal(false);
      await fetchTrips();
      fetchTripDetail(created.id);
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setCreateLoading(false);
    }
  };

  const runScenarioSimulation = async (scenarioId) => {
    if (!selectedTrip) return;
    setRunningScenario(scenarioId);
    setSimulationResult(null);
    try {
      const res = await authFetch(
        `/api/v1/cold-chain/trips/${selectedTrip.id}/simulate-scenario/${scenarioId}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reset_previous_telemetry: true }),
        }
      );
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Giả lập kịch bản thất bại.');
      }
      const result = await res.json();
      setSimulationResult(result);
      // Cập nhật lại chi tiết chuyến xe sau khi giả lập
      await fetchTripDetail(selectedTrip.id);
      fetchTrips();
    } catch (err) {
      alert(`Lỗi chạy kịch bản: ${err.message}`);
    } finally {
      setRunningScenario(null);
    }
  };

  // 5 kịch bản cảm biến mẫu (S-42)
  const SCENARIOS = [
    {
      id: 1,
      name: 'Kịch bản 1: Không vượt ngưỡng',
      badge: 'Bình thường',
      color: 'border-emerald-200 bg-emerald-50 text-emerald-800 hover:bg-emerald-100',
      icon: <CheckCircle2 className="w-5 h-5 text-emerald-600" />,
      desc: 'Duy trì ổn định trong dải an toàn (3.5°C - 5.0°C) suốt hành trình.',
      expected: '0 vi phạm (Đạt chuẩn 100%)',
    },
    {
      id: 2,
      name: 'Kịch bản 2: Vượt ngưỡng 10 phút (Mở cửa xe)',
      badge: '< 30 phút',
      color: 'border-blue-200 bg-blue-50 text-blue-800 hover:bg-blue-100',
      icon: <Clock className="w-5 h-5 text-blue-600" />,
      desc: 'Mở cửa xe bốc dỡ hàng làm nhiệt độ tăng lên 13.5°C trong 10 phút rồi giảm về 4°C.',
      expected: 'KHÔNG tính là vi phạm (độ trễ 30 phút)',
    },
    {
      id: 3,
      name: 'Kịch bản 3: Vượt ngưỡng liên tục 45 phút (> 30 phút)',
      badge: '> 30 phút',
      color: 'border-rose-200 bg-rose-50 text-rose-800 hover:bg-rose-100',
      icon: <Flame className="w-5 h-5 text-rose-600" />,
      desc: 'Hỏng lốc lạnh, nhiệt độ vượt 8°C liên tục 45 phút (đỉnh 16.5°C) mới sửa xong.',
      expected: 'Tính 1 vi phạm & Ghi Hash Chain mọi lô',
    },
    {
      id: 4,
      name: 'Kịch bản 4: Hai lần vượt cách nhau dưới 5 phút',
      badge: 'Gộp vi phạm',
      color: 'border-amber-200 bg-amber-50 text-amber-800 hover:bg-amber-100',
      icon: <AlertTriangle className="w-5 h-5 text-amber-600" />,
      desc: 'Lần 1 vượt 18p, hạ nhiệt 3p (< 5p), lần 2 vượt 20p. Tự động gộp thành 1 đợt 41 phút.',
      expected: 'Gộp thành 1 vi phạm duy nhất',
    },
    {
      id: 5,
      name: 'Kịch bản 5: Vượt qua nửa đêm (Cross-midnight)',
      badge: 'Nửa đêm',
      color: 'border-purple-200 bg-purple-50 text-purple-800 hover:bg-purple-100',
      icon: <Moon className="w-5 h-5 text-purple-600" />,
      desc: 'Bắt đầu lúc 23:40 đêm hôm trước, kéo dài qua 00:00 đến 00:25 sáng hôm sau (45 phút).',
      expected: '1 vi phạm liên tục qua nửa đêm',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 rounded-2xl p-6 text-white shadow-xl relative overflow-hidden">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-500/30 text-blue-200 border border-blue-400/30">
                Sprint 6 • User Stories S-40 -&gt; S-45
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/30">
                Độ trễ 30 phút &amp; Gộp 5 phút
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-black tracking-tight flex items-center gap-2.5">
              <ThermometerSnowflake className="w-7 h-7 text-cyan-400" />
              Giám Sát Chuỗi Lạnh &amp; Giả Lập Cảm Biến IoT
            </h1>
            <p className="text-sm text-slate-300 max-w-2xl mt-1">
              Theo dõi nhiệt độ thùng xe chuyên dụng, tự động phát hiện vi phạm bảo quản có độ trễ 30 phút,
              ghi nhận vào Hash Chain của toàn bộ lô hàng trên chuyến xe và phát cảnh báo khi bàn giao (S-45).
            </p>
          </div>

          <div className="flex items-center gap-3">
            {isLogisticsOrAdmin && (
              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white rounded-xl font-bold text-xs shadow-lg shadow-blue-500/25 transition"
              >
                <Plus className="w-4 h-4" />
                Mở Chuyến Xe Lạnh (S-40)
              </button>
            )}
            <button
              onClick={fetchTrips}
              disabled={loading}
              className="p-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-bold transition border border-white/10"
              title="Làm mới danh sách"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      {/* Main Grid: Trip List & Detail / Simulator */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Trip Selector */}
        <div className="lg:col-span-4 space-y-3">
          <div className="flex items-center justify-between text-xs font-bold text-slate-500 uppercase tracking-wider px-1">
            <span>Danh sách chuyến xe lạnh ({trips.length})</span>
            <span>Trạng thái</span>
          </div>

          {trips.length === 0 ? (
            <div className="bg-white p-6 rounded-xl border border-slate-200 text-center text-slate-500 text-sm">
              <Truck className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              Chưa có chuyến xe lạnh nào được mở.
              {isLogisticsOrAdmin && (
                <div className="mt-3">
                  <button
                    onClick={() => setShowCreateModal(true)}
                    className="text-xs font-bold text-blue-600 hover:underline"
                  >
                    + Mở chuyến xe đầu tiên
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
              {trips.map((t) => {
                const isSelected = selectedTrip?.id === t.id;
                return (
                  <div
                    key={t.id}
                    onClick={() => fetchTripDetail(t.id)}
                    className={`p-4 rounded-xl border cursor-pointer transition flex items-center justify-between gap-3 ${
                      isSelected
                        ? 'bg-blue-50/80 border-blue-400 shadow-sm ring-1 ring-blue-400/20'
                        : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'
                    }`}
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <Truck className={`w-4 h-4 ${isSelected ? 'text-blue-600' : 'text-slate-400'}`} />
                        <span className="font-bold text-sm text-slate-900 truncate">{t.vehicle_code}</span>
                      </div>
                      <div className="text-xs text-slate-500 font-mono mt-0.5">{t.trip_code}</div>
                      <div className="text-[11px] text-slate-600 mt-1 flex items-center gap-2">
                        <span>Đang chở: <b className="text-slate-800">{t.batches?.length || 0} lô</b></span>
                        <span>•</span>
                        <span>Dải nhiệt: <b className="text-blue-700">{t.min_temperature}° - {t.max_temperature}°C</b></span>
                      </div>
                    </div>

                    <div className="text-right shrink-0">
                      <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 border border-blue-200">
                        {t.status}
                      </span>
                      {t.violations_count > 0 && (
                        <div className="mt-1 text-[10px] font-bold text-rose-600 flex items-center justify-end gap-1">
                          <AlertTriangle className="w-3 h-3" />
                          {t.violations_count} vi phạm
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Simulator & Details */}
        <div className="lg:col-span-8 space-y-6">
          {!selectedTrip ? (
            <div className="bg-white p-12 rounded-2xl border border-slate-200 text-center text-slate-400">
              <ThermometerSnowflake className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <p className="text-sm font-medium">Chọn một chuyến xe từ danh sách bên trái để bắt đầu giám sát hoặc giả lập cảm biến.</p>
            </div>
          ) : (
            <>
              {/* Trip Overview Card */}
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-4 mb-4 border-slate-100">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-lg font-black text-slate-900 flex items-center gap-2">
                        <Truck className="w-5 h-5 text-blue-600" />
                        Chuyến Xe {selectedTrip.vehicle_code}
                      </h2>
                      <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-bold border border-slate-200">
                        {selectedTrip.trip_code}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Đơn vị vận chuyển: <span className="font-bold text-slate-800">{selectedTrip.carrier_org_name || 'N/A'}</span> • 
                      Tài xế: <span className="font-bold text-slate-800">{selectedTrip.driver_name || 'N/A'}</span>
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold px-3 py-1 rounded-lg bg-cyan-50 border border-cyan-200 text-cyan-800 flex items-center gap-1.5">
                      <ThermometerSnowflake className="w-4 h-4 text-cyan-600" />
                      Ngưỡng an toàn: {selectedTrip.min_temperature}°C đến {selectedTrip.max_temperature}°C
                    </span>
                  </div>
                </div>

                {/* Batches on Trip */}
                <div className="space-y-1.5">
                  <div className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-emerald-600" />
                    Lô hàng trên chuyến ({selectedTrip.batches?.length || 0}):
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {selectedTrip.batches?.map((b) => (
                      <span
                        key={b.batch_id}
                        className="px-2.5 py-1 rounded-lg bg-slate-100 border border-slate-200 text-xs font-mono font-bold text-slate-800 flex items-center gap-1.5"
                      >
                        📦 {b.batch_code} ({b.product_name})
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* 5-Scenario Sensor Simulator Tool (S-42) - Chỉ hiển thị cho Carrier / Admin */}
              {isLogisticsOrAdmin && (
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                      <Play className="w-5 h-5 text-blue-600 fill-blue-600" />
                      Công Cụ Giả Lập Cảm Biến Nhiệt Độ (User Story S-42)
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Bấm vào từng kịch bản bên dưới để bơm chuỗi dữ liệu cảm biến vào chuyến xe và kiểm tra thuật toán:
                    </p>
                  </div>
                  <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                    5 Kịch bản mẫu
                  </span>
                </div>

                {/* 5 Scenario Buttons */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
                  {SCENARIOS.map((sc) => {
                    const isRunning = runningScenario === sc.id;
                    return (
                      <button
                        key={sc.id}
                        onClick={() => runScenarioSimulation(sc.id)}
                        disabled={runningScenario !== null}
                        className={`p-3.5 rounded-xl border text-left transition relative flex flex-col justify-between ${sc.color} ${
                          isRunning ? 'ring-2 ring-blue-500 animate-pulse' : ''
                        }`}
                      >
                        <div>
                          <div className="flex items-center justify-between gap-1 mb-1.5">
                            {sc.icon}
                            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-white/80 border">
                              {sc.badge}
                            </span>
                          </div>
                          <div className="font-bold text-xs leading-snug">{sc.name}</div>
                          <p className="text-[11px] opacity-85 mt-1 leading-relaxed">{sc.desc}</p>
                        </div>

                        <div className="mt-3 pt-2 border-t border-black/5 flex items-center justify-between text-[11px] font-bold">
                          <span>Dự kiến: {sc.expected}</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </div>
                      </button>
                    );
                  })}
                </div>

                {/* Simulation Execution Result Box */}
                {simulationResult && (
                  <div
                    className={`p-4 rounded-xl border transition animate-in fade-in ${
                      simulationResult.is_violated
                        ? 'bg-rose-50 border-rose-300 text-rose-900'
                        : 'bg-emerald-50 border-emerald-300 text-emerald-900'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-3">
                        <div
                          className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 mt-0.5 ${
                            simulationResult.is_violated ? 'bg-rose-600 text-white' : 'bg-emerald-600 text-white'
                          }`}
                        >
                          {simulationResult.is_violated ? (
                            <AlertTriangle className="w-5 h-5" />
                          ) : (
                            <CheckCircle2 className="w-5 h-5" />
                          )}
                        </div>
                        <div>
                          <div className="text-sm font-bold flex items-center gap-2">
                            {simulationResult.scenario_name}
                            <span
                              className={`text-[11px] px-2 py-0.5 rounded-full font-extrabold uppercase ${
                                simulationResult.is_violated
                                  ? 'bg-rose-200 text-rose-900'
                                  : 'bg-emerald-200 text-emerald-900'
                              }`}
                            >
                              {simulationResult.is_violated ? 'KÍCH HOẠT VI PHẠM' : 'AN TOÀN - KHÔNG VI PHẠM'}
                            </span>
                          </div>
                          <p className="text-xs mt-1 leading-relaxed">{simulationResult.rule_explanation}</p>
                          <div className="text-xs mt-2 flex flex-wrap items-center gap-3 font-semibold">
                            <span>Điểm cảm biến nạp: <b>{simulationResult.readings_injected}</b></span>
                            <span>•</span>
                            <span>Số đợt vi phạm ghi nhận: <b>{simulationResult.violations_count}</b></span>
                            {simulationResult.hash_chain_updated && (
                              <span className="px-2 py-0.5 rounded bg-rose-200/80 text-rose-950 font-bold border border-rose-300 flex items-center gap-1">
                                <Hash className="w-3.5 h-3.5" />
                                Đã ghi sự kiện COLD_CHAIN_VIOLATION vào Hash Chain của mọi lô trên xe (S-45)
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              )}

              {/* Recorded Violations & Handover Warning Demonstration (S-45) */}
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-rose-600" />
                    Sự Kiện Vi Phạm Đã Ghi Nhận (Chuỗi Khối Hash Chain - S-45)
                  </h3>
                  <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700">
                    {selectedTrip.violations?.length || 0} vi phạm
                  </span>
                </div>

                {(!selectedTrip.violations || selectedTrip.violations.length === 0) ? (
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-center text-xs text-slate-500">
                    Chuyến xe hiện tại chưa ghi nhận vi phạm nhiệt độ nào.
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {selectedTrip.violations.map((v) => (
                      <div
                        key={v.id}
                        className="p-3.5 bg-rose-50/80 border border-rose-200 rounded-xl text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                      >
                        <div>
                          <div className="font-bold text-rose-900 flex items-center gap-2">
                            <span>Vi phạm nhiệt độ cao ({v.violation_type})</span>
                            <span className="px-2 py-0.5 rounded text-[10px] bg-rose-200 text-rose-900 font-bold">
                              Kéo dài {v.duration_minutes} phút
                            </span>
                            <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-100 text-emerald-800 font-bold border border-emerald-200 flex items-center gap-1 font-mono">
                              <Hash className="w-3 h-3" /> HASH RECORDED
                            </span>
                          </div>
                          <div className="text-slate-600 mt-1">
                            Nhiệt độ đỉnh: <b className="text-rose-700">{v.peak_temperature}°C</b> (Ngưỡng cho phép: {v.threshold}°C) • 
                            Bắt đầu: {new Date(v.started_at).toLocaleTimeString('vi-VN')} - Kết thúc: {new Date(v.ended_at).toLocaleTimeString('vi-VN')}
                          </div>
                        </div>

                        {/* Handover Warning Badge Demo */}
                        <div className="p-2 bg-amber-50 border border-amber-200 rounded-lg text-amber-900 text-[11px] font-semibold max-w-xs shrink-0">
                          ⚠️ Cảnh báo bàn giao (S-45): Lô hàng này sẽ kích hoạt cờ cảnh báo khi đơn vị tiếp nhận kiểm định phẩm chất.
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Modal Mở chuyến xe lạnh mới (S-40) */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 bg-slate-800 text-white flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Truck className="w-5 h-5 text-cyan-400" />
                <span className="font-bold text-sm">Mở Chuyến Vận Chuyển Lạnh (User Story S-40)</span>
              </div>
              <button onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateTrip} className="p-6 space-y-4 text-xs">
              {errorMsg && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700">
                  {errorMsg}
                </div>
              )}

              <div>
                <label className="block font-bold text-slate-700 mb-1">Biển số xe / Mã thùng lạnh *</label>
                <input
                  type="text"
                  required
                  value={newVehicle}
                  onChange={(e) => setNewVehicle(e.target.value)}
                  placeholder="REEFER-51D-888.99"
                  className="w-full px-3 py-2 border rounded-xl font-mono font-bold focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Tên tài xế phụ trách</label>
                <input
                  type="text"
                  value={newDriver}
                  onChange={(e) => setNewDriver(e.target.value)}
                  placeholder="Nguyễn Văn Tài Xế"
                  className="w-full px-3 py-2 border rounded-xl font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Nhiệt độ tối thiểu (°C)</label>
                  <input
                    type="number"
                    step="0.5"
                    value={minTemp}
                    onChange={(e) => setMinTemp(e.target.value)}
                    className="w-full px-3 py-2 border rounded-xl font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Nhiệt độ tối đa (°C)</label>
                  <input
                    type="number"
                    step="0.5"
                    value={maxTemp}
                    onChange={(e) => setMaxTemp(e.target.value)}
                    className="w-full px-3 py-2 border rounded-xl font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  Chọn các lô hàng đang chở trên xe * ({selectedBatchIds.length} đã chọn)
                </label>
                <div className="max-h-40 overflow-y-auto border rounded-xl divide-y p-1">
                  {availableBatches.map((b) => {
                    const isChecked = selectedBatchIds.includes(b.id);
                    return (
                      <label
                        key={b.id}
                        className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition ${
                          isChecked ? 'bg-blue-50 font-bold' : 'hover:bg-slate-50'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedBatchIds([...selectedBatchIds, b.id]);
                            } else {
                              setSelectedBatchIds(selectedBatchIds.filter((id) => id !== b.id));
                            }
                          }}
                          className="rounded text-blue-600 focus:ring-0"
                        />
                        <span className="font-mono text-[11px]">{b.batch_code}</span>
                        <span className="text-slate-600 truncate">{b.product_name}</span>
                        <span className="ml-auto text-slate-400 font-mono text-[10px]">{b.remaining_quantity} {b.unit}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="pt-3 border-t flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border rounded-xl text-slate-600 hover:bg-slate-50 font-bold"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={createLoading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-bold shadow-sm"
                >
                  {createLoading ? 'Đang tạo...' : 'Xác Nhận Khởi Hành (S-40)'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
