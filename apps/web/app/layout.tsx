export const metadata = {
  title: 'Jarvix - AI Crypto Command Center',
  description: 'AI-powered crypto trading assistant',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
