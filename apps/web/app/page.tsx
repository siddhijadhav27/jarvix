export default function Home() {
  return (
    <div style={{ padding: '40px', fontFamily: 'Arial, sans-serif', background: '#0a0a0a', color: '#fff', minHeight: '100vh' }}>
      <h1 style={{ fontSize: '48px', marginBottom: '10px' }}>🚀 Jarvix</h1>
      <p style={{ fontSize: '20px', color: '#888', marginBottom: '40px' }}>AI-Powered Crypto Command Center</p>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', maxWidth: '900px' }}>
        <div style={{ background: '#1a1a1a', padding: '24px', borderRadius: '12px', border: '1px solid #333' }}>
          <h3>📊 Portfolio</h3>
          <p>$100,000.00</p>
          <p style={{ color: '#4ade80' }}>+2.4%</p>
        </div>
        
        <div style={{ background: '#1a1a1a', padding: '24px', borderRadius: '12px', border: '1px solid #333' }}>
          <h3>💰 ETH</h3>
          <p>$2,007.01</p>
          <p style={{ color: '#4ade80' }}>+1.09%</p>
        </div>
        
        <div style={{ background: '#1a1a1a', padding: '24px', borderRadius: '12px', border: '1px solid #333' }}>
          <h3>₿ BTC</h3>
          <p>$73,447.00</p>
          <p style={{ color: '#4ade80' }}>+0.29%</p>
        </div>
      </div>
      
      <div style={{ marginTop: '40px', padding: '20px', background: '#1a1a1a', borderRadius: '12px', maxWidth: '900px', border: '1px solid #333' }}>
        <h3>🧠 AI Status</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px', marginTop: '10px' }}>
          <div>✅ Multi-LLM Router</div>
          <div>✅ Natural Language Commands</div>
          <div>✅ Context Awareness + Memory</div>
          <div>✅ Behavioral Finance Guard</div>
          <div>✅ Ghost Mode Onboarding</div>
          <div>⏳ Real-Time Price Feeds</div>
        </div>
      </div>
      
      <div style={{ marginTop: '20px', color: '#666', fontSize: '14px' }}>
        Phase 1 Complete • 28/28 Tests Passing • Ready for Phase 2
      </div>
    </div>
  )
}
