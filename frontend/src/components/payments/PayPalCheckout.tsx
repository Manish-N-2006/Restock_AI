import React, { useEffect, useRef, useState } from 'react';
import { apiFetch } from '../../api/client';
import {
  CreditCard,
  CheckCircle2,
  AlertCircle,
  Clock,
  ShieldCheck,
  RefreshCw,
  ArrowRight,
  Info,
  Zap,
} from 'lucide-react';

export interface RecoveryOrderData {
  order_id: string;
  sku_id: string;
  product_name: string;
  source_store_id: string;
  channel: string;
  quantity: number;
  unit_price: number;
  total_amount: number;
  currency: string;
  status: string; // "CREATED" | "PENDING_PAYMENT" | "PAID" | "CANCELLED"
  fulfillment_status: string; // "UNFULFILLED" | "PROCESSING" | "SHIPPED"
  payment_id?: string;
  buyer_name?: string;
  buyer_email?: string;
  paid_at?: string;
}

export interface CaptureResult {
  payment_id: string;
  recovery_order_id: string;
  paypal_order_id: string;
  paypal_capture_id: string;
  status: string;
  amount: number;
  currency: string;
  fee_amount: number;
  net_amount: number;
  payer_id?: string;
  payer_email?: string;
  payer_name?: string;
  captured_at: string;
}

interface PayPalCheckoutProps {
  order: RecoveryOrderData;
  onPaymentSuccess?: (result: CaptureResult) => void;
  onClose?: () => void;
  isModal?: boolean;
}

declare global {
  interface Window {
    paypal?: any;
  }
}

export const PayPalCheckout: React.FC<PayPalCheckoutProps> = ({
  order,
  onPaymentSuccess,
  onClose,
  isModal = false,
}) => {
  const [loadingConfig, setLoadingConfig] = useState(true);
  const [sdkReady, setSdkReady] = useState(false);
  const [clientConfig, setClientConfig] = useState<{
    client_id: string;
    currency: string;
    mode: string;
    is_mock: boolean;
    is_configured: boolean;
  } | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingMessage, setProcessingMessage] = useState('');
  const [captureResult, setCaptureResult] = useState<CaptureResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [cancelMessage, setCancelMessage] = useState<string | null>(null);
  const [orderStatus, setOrderStatus] = useState(order.status);

  const buttonContainerRef = useRef<HTMLDivElement>(null);

  // 1. Fetch PayPal client configuration from ReStockAI backend
  useEffect(() => {
    let mounted = true;
    setLoadingConfig(true);

    apiFetch('/api/payments/config')
      .then(async (res) => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `HTTP ${res.status}`);
        }
        return res.json();
      })
      .then((config) => {
        if (!mounted) return;
        setClientConfig(config);

        if (!config.is_configured && !config.is_mock) {
          setLoadingConfig(false);
          setErrorMessage('PayPal Sandbox credentials not configured. Please supply RESTOCKAI_PAYPAL_CLIENT_ID and RESTOCKAI_PAYPAL_CLIENT_SECRET.');
          return;
        }

        const clientId = config.client_id || 'sb';
        const currency = order.currency || config.currency || 'USD';

        // Check if PayPal SDK script is already loaded
        const scriptId = 'paypal-js-sdk';
        const existingScript = document.getElementById(scriptId) as HTMLScriptElement;

        if (existingScript && window.paypal) {
          setSdkReady(true);
          setLoadingConfig(false);
          return;
        }

        if (existingScript) {
          existingScript.remove();
        }

        const script = document.createElement('script');
        script.id = scriptId;
        // In sandbox mode, unbranded credit card without merchant ACDC can trigger errors; disable card funding to present official gold PayPal button
        script.src = `https://www.paypal.com/sdk/js?client-id=${clientId}&currency=${currency}&components=buttons&disable-funding=credit,card`;
        script.async = true;

        script.onload = () => {
          if (mounted) {
            setSdkReady(true);
            setLoadingConfig(false);
          }
        };

        script.onerror = () => {
          if (mounted) {
            setLoadingConfig(false);
            setErrorMessage('Unable to load PayPal JavaScript SDK. Verify network connection to paypal.com.');
          }
        };

        document.body.appendChild(script);
      })
      .catch((err) => {
        if (mounted) {
          setLoadingConfig(false);
          setErrorMessage(`Failed to fetch PayPal config: ${err.message}`);
        }
      });

    return () => {
      mounted = false;
    };
  }, [order.currency]);

  // 2. Render PayPal standard buttons once SDK is ready
  useEffect(() => {
    if (!sdkReady || !window.paypal || !buttonContainerRef.current || orderStatus === 'PAID') {
      return;
    }

    buttonContainerRef.current.innerHTML = '';

    try {
      window.paypal
        .Buttons({
          style: {
            layout: 'vertical',
            color: 'gold',
            shape: 'rect',
            label: 'pay',
            height: 44,
          },

          // Step 1: Server creates PayPal Order strictly from persisted order amount
          createOrder: async () => {
            setErrorMessage(null);
            setCancelMessage(null);
            setIsProcessing(true);
            setProcessingMessage('Creating secure PayPal order...');

            try {
              const res = await apiFetch('/api/payments/paypal/create-order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  recovery_order_id: order.order_id,
                  idempotency_key: `chk-${order.order_id}-${Date.now()}`,
                }),
              });

              if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || 'Failed to initialize PayPal order');
              }

              const data = await res.json();
              setIsProcessing(false);
              return data.paypal_order_id;
            } catch (err: any) {
              setIsProcessing(false);
              setErrorMessage(err.message || 'Payment initiation failed.');
              throw err;
            }
          },

          // Step 2: Buyer approved in PayPal -> Server verifies and captures payment
          onApprove: async (data: any) => {
            setIsProcessing(true);
            setProcessingMessage('Buyer approved! Verifying & capturing PayPal Sandbox payment...');

            try {
              const res = await apiFetch('/api/payments/paypal/capture', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  paypal_order_id: data.orderID,
                  recovery_order_id: order.order_id,
                }),
              });

              if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || 'Payment capture failed');
              }

              const captureData: CaptureResult = await res.json();
              setIsProcessing(false);
              setCaptureResult(captureData);
              setOrderStatus('PAID');
              onPaymentSuccess?.(captureData);
            } catch (err: any) {
              setIsProcessing(false);
              setErrorMessage(err.message || 'Payment capture validation failed.');
            }
          },

          // Step 3: Buyer cancelled PayPal checkout session
          onCancel: async (data: any) => {
            setIsProcessing(false);
            setCancelMessage('Payment session was cancelled. You can retry checkout at any time.');

            if (data.orderID) {
              apiFetch('/api/payments/paypal/cancel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  paypal_order_id: data.orderID,
                  recovery_order_id: order.order_id,
                  reason: 'Buyer cancelled during checkout',
                }),
              }).catch(console.error);
            }
          },

          // Step 4: Generic SDK error
          onError: (err: any) => {
            setIsProcessing(false);
            setErrorMessage((prev) => prev || 'PayPal checkout encountered an error. Please try again or refresh.');
            console.error('PayPal Buttons Error:', err);
          },
        })
        .render(buttonContainerRef.current);
    } catch (e: any) {
      console.error('Failed to render PayPal Buttons:', e);
    }
  }, [sdkReady, order.order_id, orderStatus]);

  // Direct sandbox test capture helper (for headless / automated testing & environments)
  const handleDirectSandboxCapture = async () => {
    setIsProcessing(true);
    setErrorMessage(null);
    setCancelMessage(null);
    setProcessingMessage('Simulating end-to-end PayPal Sandbox capture...');

    try {
      // 1. Create order
      const createRes = await apiFetch('/api/payments/paypal/create-order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recovery_order_id: order.order_id,
          idempotency_key: `sim-${order.order_id}-${Date.now()}`,
        }),
      });

      if (!createRes.ok) {
        const err = await createRes.json();
        throw new Error(err.detail || 'Create order failed');
      }

      const createData = await createRes.json();

      // 2. Capture order
      const captureRes = await apiFetch('/api/payments/paypal/capture', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          paypal_order_id: createData.paypal_order_id,
          recovery_order_id: order.order_id,
        }),
      });

      if (!captureRes.ok) {
        const err = await captureRes.json();
        throw new Error(err.detail || 'Capture failed');
      }

      const capData: CaptureResult = await captureRes.json();
      setCaptureResult(capData);
      setOrderStatus('PAID');
      setIsProcessing(false);
      onPaymentSuccess?.(capData);
    } catch (err: any) {
      setIsProcessing(false);
      setErrorMessage(err.message || 'Direct Sandbox Capture failed');
    }
  };

  return (
    <div className={`bg-white rounded-xl shadow-lg border border-slate-200 overflow-hidden ${isModal ? 'max-w-lg w-full' : 'w-full'}`}>
      {/* Header */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-600/30 border border-indigo-400/40 flex items-center justify-center text-indigo-300">
            <CreditCard className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-base leading-tight">PayPal Commercial Checkout</h3>
              {clientConfig?.is_configured ? (
                <span className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-[10px] px-2 py-0.5 rounded-full font-medium">
                  Live Sandbox
                </span>
              ) : clientConfig?.is_mock ? (
                <span className="bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[10px] px-2 py-0.5 rounded-full font-medium">
                  Mock Mode
                </span>
              ) : null}
            </div>
            <p className="text-xs text-slate-300">
              {clientConfig?.is_configured
                ? 'Official PayPal Sandbox Orders API v2'
                : clientConfig?.is_mock
                ? 'Mock Simulation Engine (Sandbox Offline)'
                : 'PayPal Orders API v2'}
            </p>
          </div>
        </div>
        {isModal && onClose && (
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white text-xl font-medium w-8 h-8 rounded-full hover:bg-white/10 flex items-center justify-center transition"
          >
            &times;
          </button>
        )}
      </div>

      <div className="p-6 space-y-5">
        {/* Business Logic Explanation: Who is paying whom */}
        <div className="bg-gradient-to-r from-indigo-50 to-blue-50 border border-indigo-200/80 rounded-xl p-3.5 text-xs text-indigo-950 space-y-1.5 shadow-xs">
          <div className="flex items-center gap-2 font-bold text-indigo-900">
            <Info className="w-4 h-4 text-indigo-600 flex-shrink-0" />
            <span>Autonomous Settlement Context: Buyer Payment</span>
          </div>
          <p className="text-slate-600 leading-relaxed text-[11px]">
            In this autonomous commerce cycle, <strong>you are acting on behalf of the external commercial buyer ({order.buyer_name || 'Metro Retail Mart'})</strong>.
            You are paying <strong>${order.total_amount.toFixed(2)} USD</strong> to <strong>ReStockAI (Store A's merchant account)</strong> to acquire perishable surplus before expiry.
            Once payment is captured, the <strong>Fulfillment Agent (Tom Becker)</strong> releases the stock, and the <strong>Finance Agent (Linda Zhang)</strong> audits and reconciles the margin.
          </p>
        </div>

        {/* Order Summary Card */}
        <div className="bg-slate-50 rounded-lg p-4 border border-slate-200/80">
          <div className="flex items-center justify-between mb-3 border-b border-slate-200 pb-2">
            <div>
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Recovery Order</span>
              <p className="font-mono text-sm font-bold text-slate-800">{order.order_id}</p>
            </div>
            <div className="flex gap-2">
              <span
                className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                  orderStatus === 'PAID'
                    ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                    : 'bg-amber-100 text-amber-800 border border-amber-300'
                }`}
              >
                {orderStatus}
              </span>
              <span className="text-xs px-2.5 py-1 rounded-full font-medium bg-slate-200 text-slate-700 border border-slate-300">
                Fulfillment: {order.fulfillment_status}
              </span>
            </div>
          </div>

          <div className="space-y-2 text-sm text-slate-600">
            <div className="flex justify-between">
              <span>Item / SKU:</span>
              <span className="font-medium text-slate-800">
                {order.product_name} <span className="text-xs font-mono text-slate-500">({order.sku_id})</span>
              </span>
            </div>
            <div className="flex justify-between">
              <span>Channel / Store:</span>
              <span className="font-medium text-slate-800">
                {order.channel} &bull; {order.source_store_id}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Quantity:</span>
              <span className="font-medium text-slate-800">
                {order.quantity} units @ ${order.unit_price.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between border-t border-slate-200 pt-2 text-base font-semibold text-slate-900">
              <span>Total Payable:</span>
              <span className="text-indigo-700 font-bold">
                ${order.total_amount.toFixed(2)} {order.currency || 'USD'}
              </span>
            </div>
          </div>
        </div>

        {/* Processing State */}
        {isProcessing && (
          <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4 flex items-center gap-3 text-indigo-800">
            <RefreshCw className="w-5 h-5 animate-spin text-indigo-600" />
            <div className="text-xs">
              <p className="font-semibold">{processingMessage}</p>
              <p className="text-indigo-600">Please do not close or refresh this window.</p>
            </div>
          </div>
        )}

        {/* Error Notification */}
        {errorMessage && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3 text-red-800">
            <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-600 mt-0.5" />
            <div className="text-xs">
              <p className="font-semibold">Payment Error</p>
              <p>{errorMessage}</p>
            </div>
          </div>
        )}

        {/* Cancellation Notification */}
        {cancelMessage && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-start gap-3 text-amber-800">
            <Clock className="w-5 h-5 flex-shrink-0 text-amber-600 mt-0.5" />
            <div className="text-xs">
              <p className="font-semibold">Session Cancelled</p>
              <p>{cancelMessage}</p>
            </div>
          </div>
        )}

        {/* SUCCESS CONFIRMATION VIEW */}
        {orderStatus === 'PAID' && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-5 space-y-4">
            <div className="flex items-center gap-3 text-emerald-800">
              <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600 border border-emerald-300">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div>
                <h4 className="font-bold text-sm">Payment Verified & Captured!</h4>
                <p className="text-xs text-emerald-700">Official PayPal Orders v2 transaction complete</p>
              </div>
            </div>

            <div className="bg-white rounded-md p-3 border border-emerald-200 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500">PayPal Capture ID:</span>
                <span className="font-mono font-semibold text-slate-800">
                  {captureResult?.paypal_capture_id || order.payment_id || 'CAP-CONFIRMED'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Internal Payment ID:</span>
                <span className="font-mono text-slate-700">{captureResult?.payment_id || order.payment_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Gross Captured:</span>
                <span className="font-semibold text-emerald-700">
                  ${(captureResult?.amount || order.total_amount).toFixed(2)} {order.currency}
                </span>
              </div>
              {captureResult?.fee_amount ? (
                <div className="flex justify-between">
                  <span className="text-slate-500">PayPal Fee:</span>
                  <span className="text-slate-600">${captureResult.fee_amount.toFixed(2)}</span>
                </div>
              ) : null}
              {captureResult?.payer_email && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Payer Email:</span>
                  <span className="text-slate-700">{captureResult.payer_email}</span>
                </div>
              )}
              <div className="flex justify-between border-t border-slate-100 pt-1.5 text-slate-500">
                <span>Fulfillment Status:</span>
                <span className="font-medium text-amber-700">Decoupled ({order.fulfillment_status})</span>
              </div>
            </div>

            {onClose && (
              <button
                onClick={onClose}
                className="w-full bg-slate-900 text-white font-medium py-2 rounded-lg text-xs hover:bg-slate-800 transition flex items-center justify-center gap-2"
              >
                <span>Close Checkout</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        )}

        {/* PAYPAL CHECKOUT ACTIONS */}
        {orderStatus !== 'PAID' && (
          <div className="space-y-4">
            {loadingConfig && (
              <div className="text-center py-6 text-xs text-slate-500 flex flex-col items-center gap-2">
                <RefreshCw className="w-5 h-5 animate-spin text-slate-400" />
                <span>Loading PayPal Sandbox SDK...</span>
              </div>
            )}

            {/* PayPal Buttons Target Container */}
            <div ref={buttonContainerRef} className="min-h-[44px]" />

            {/* Instant Fast Settlement Option for seamless testing / demo flow */}
            <div className="pt-2 border-t border-slate-100 space-y-2">
              <button
                onClick={handleDirectSandboxCapture}
                disabled={isProcessing}
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2.5 px-4 rounded-lg text-xs shadow-xs flex items-center justify-center gap-2 transition disabled:opacity-50 cursor-pointer"
              >
                <Zap className="w-4 h-4 text-amber-300" />
                <span>Instant 1-Click Sandbox Settlement (Demo / Evaluation Mode)</span>
              </button>
              <div className="flex items-center justify-between text-[10px] text-slate-500 px-1">
                <span>💡 Uses Orders API v2 capture</span>
                {errorMessage && (
                  <button
                    onClick={() => {
                      setErrorMessage(null);
                      setCancelMessage(null);
                    }}
                    className="text-indigo-600 hover:underline font-bold cursor-pointer"
                  >
                    Clear error & retry
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Security Footer */}
      <div className="bg-slate-50 border-t border-slate-100 px-6 py-2.5 flex items-center justify-between text-[11px] text-slate-500">
        <div className="flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
          <span>PayPal Orders API v2 &bull; 256-bit TLS</span>
        </div>
        <span className="font-mono text-[10px] text-slate-400">ReStockAI v0.1.0</span>
      </div>
    </div>
  );
};
