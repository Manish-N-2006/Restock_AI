import React, { useEffect, useState } from 'react';
import {
  CreditCard,
  ShoppingBag,
  DollarSign,
  CheckCircle2,
  Clock,
  PlusCircle,
  RefreshCw,
  PackageCheck,
  ShieldCheck,
  AlertTriangle,
} from 'lucide-react';
import { PayPalCheckout, RecoveryOrderData, CaptureResult } from '../components/payments/PayPalCheckout';
import { API_BASE_URL } from '../api/config';
import { apiFetch } from '../api/client';

export const RecoveryOrdersPage: React.FC = () => {
  const [orders, setOrders] = useState<RecoveryOrderData[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [selectedOrder, setSelectedOrder] = useState<RecoveryOrderData | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const fetchOrders = () => {
    setLoading(true);
    setFetchError(null);
    apiFetch('/api/payments/orders/eligible')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}: Backend service unreachable`);
        return res.json();
      })
      .then((data) => {
        if (Array.isArray(data)) {
          setOrders(data);
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to fetch orders:', err);
        setFetchError(`Backend offline: Could not connect to FastAPI backend (${API_BASE_URL || window.location.origin}). Verify the backend service is running and CORS is configured.`);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchOrders();
  }, []);

  const handleCreateSample = async () => {
    setIsCreating(true);
    try {
      const res = await apiFetch('/api/payments/orders/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sku_id: 'YOG-001',
          product_name: 'Greek Yogurt 500g',
          source_store_id: 'STORE_A',
          channel: 'DISCOUNT_MARKETPLACE',
          quantity: 25,
          unit_price: 2.20,
          currency: 'USD',
          buyer_name: 'Metro Retail Mart',
          buyer_email: 'buyer@metroretail.com',
        }),
      });
      if (res.ok) {
        const newOrder = await res.json();
        setOrders((prev) => [newOrder, ...prev]);
        setSelectedOrder(newOrder);
      }
    } catch (e) {
      console.error('Error creating order:', e);
    } finally {
      setIsCreating(false);
    }
  };

  const handlePaymentSuccess = (result: CaptureResult) => {
    setOrders((prev) =>
      prev.map((o) =>
        o.order_id === result.recovery_order_id
          ? { ...o, status: 'PAID', payment_id: result.payment_id, paid_at: result.captured_at }
          : o
      )
    );
  };

  const paidCount = orders.filter((o) => o.status === 'PAID').length;
  const pendingCount = orders.filter((o) => o.status !== 'PAID').length;
  const totalRevenue = orders
    .filter((o) => o.status === 'PAID')
    .reduce((sum, o) => sum + (o.total_amount || 0), 0);

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2 text-indigo-700 font-semibold text-xs tracking-wider uppercase mb-1">
            <CreditCard className="w-4 h-4" />
            <span>Commerce & Settlement</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">PayPal Commercial Recovery Orders</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Decoupled payment settlement engine powered by PayPal Orders API v2
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchOrders}
            className="p-2 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50 transition"
            title="Refresh Orders"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleCreateSample}
            disabled={isCreating}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-xs font-medium flex items-center gap-2 shadow-xs transition disabled:opacity-50"
          >
            <PlusCircle className="w-4 h-4" />
            <span>New Recovery Order</span>
          </button>
        </div>
      </div>

      {/* Backend Offline Warning Banner */}
      {fetchError && (
        <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 flex items-start gap-3 text-amber-900 shadow-xs">
          <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <p className="font-semibold text-sm text-amber-800">Backend Server Not Detected</p>
            <p>{fetchError}</p>
            <p className="text-amber-700">Once started, click the refresh button above to load the live recovery orders.</p>
          </div>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Settled Revenue</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">${totalRevenue.toFixed(2)} USD</p>
            <p className="text-[11px] text-emerald-600 font-medium mt-0.5 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Verified in PayPal Sandbox</span>
            </p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center border border-emerald-100">
            <DollarSign className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Paid Orders</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{paidCount}</p>
            <p className="text-[11px] text-slate-500 mt-0.5">Fulfillment decoupled</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center border border-indigo-100">
            <CheckCircle2 className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Awaiting Payment</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{pendingCount}</p>
            <p className="text-[11px] text-amber-600 font-medium mt-0.5 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              <span>Ready for checkout</span>
            </p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center border border-amber-100">
            <ShoppingBag className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Orders Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <PackageCheck className="w-4 h-4 text-slate-600" />
            <h2 className="font-semibold text-sm text-slate-800">Commercial Recovery Ledger</h2>
          </div>
          <span className="text-xs text-slate-500 font-medium">{orders.length} total orders</span>
        </div>

        {loading ? (
          <div className="py-12 flex flex-col items-center justify-center text-slate-400 gap-2">
            <RefreshCw className="w-6 h-6 animate-spin text-indigo-600" />
            <span className="text-xs">Loading recovery orders...</span>
          </div>
        ) : orders.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-sm">
            <p>No commercial recovery orders found.</p>
            <button
              onClick={handleCreateSample}
              className="mt-3 text-indigo-600 hover:underline text-xs font-medium"
            >
              Click here to create a sample recovery order
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/70 text-slate-500 uppercase font-semibold text-[10px] tracking-wider">
                  <th className="py-3 px-5">Order ID</th>
                  <th className="py-3 px-5">SKU / Product</th>
                  <th className="py-3 px-5">Channel</th>
                  <th className="py-3 px-5">Store</th>
                  <th className="py-3 px-5 text-right">Qty</th>
                  <th className="py-3 px-5 text-right">Unit Price</th>
                  <th className="py-3 px-5 text-right">Total Amount</th>
                  <th className="py-3 px-5">Payment Status</th>
                  <th className="py-3 px-5">Fulfillment</th>
                  <th className="py-3 px-5 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {orders.map((order) => {
                  const isPaid = order.status === 'PAID';
                  return (
                    <tr key={order.order_id} className="hover:bg-slate-50/80 transition">
                      <td className="py-3.5 px-5 font-mono font-medium text-slate-800">
                        {order.order_id}
                      </td>
                      <td className="py-3.5 px-5">
                        <div className="font-semibold text-slate-900">{order.product_name}</div>
                        <div className="text-[10px] font-mono text-slate-400">{order.sku_id}</div>
                      </td>
                      <td className="py-3.5 px-5 text-slate-600 font-medium">
                        {order.channel}
                      </td>
                      <td className="py-3.5 px-5 text-slate-600">{order.source_store_id}</td>
                      <td className="py-3.5 px-5 text-right font-medium text-slate-800">{order.quantity}</td>
                      <td className="py-3.5 px-5 text-right font-medium text-slate-800">
                        ${order.unit_price.toFixed(2)}
                      </td>
                      <td className="py-3.5 px-5 text-right font-bold text-indigo-700">
                        ${order.total_amount.toFixed(2)} {order.currency}
                      </td>
                      <td className="py-3.5 px-5">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold ${
                            isPaid
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                              : 'bg-amber-100 text-amber-800 border border-amber-200'
                          }`}
                        >
                          {isPaid ? <CheckCircle2 className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
                          <span>{order.status}</span>
                        </span>
                      </td>
                      <td className="py-3.5 px-5">
                        <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200 font-medium">
                          {order.fulfillment_status}
                        </span>
                      </td>
                      <td className="py-3.5 px-5 text-center">
                        <button
                          onClick={() => setSelectedOrder(order)}
                          className={`px-3 py-1.5 rounded-lg text-xs font-medium inline-flex items-center gap-1.5 transition ${
                            isPaid
                              ? 'bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-300'
                              : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-xs'
                          }`}
                        >
                          <CreditCard className="w-3.5 h-3.5" />
                          <span>{isPaid ? 'View Receipt' : 'Pay via PayPal'}</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Checkout Modal */}
      {selectedOrder && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="relative animate-in fade-in zoom-in duration-200">
            <PayPalCheckout
              order={selectedOrder}
              isModal={true}
              onClose={() => setSelectedOrder(null)}
              onPaymentSuccess={handlePaymentSuccess}
            />
          </div>
        </div>
      )}
    </div>
  );
};
