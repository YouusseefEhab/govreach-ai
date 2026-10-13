
import { useEffect, useState } from "react"
import { checkBackend } from "../services/api"

function Home() {
  const [backendStatus, setBackendStatus] = useState("Checking...")
  const [error, setError] = useState("")

  useEffect(() => {
    checkBackend()
      .then((data) => setBackendStatus(data.status))
      .catch(() => {
        setBackendStatus("Unavailable")
        setError("Make sure the FastAPI backend is running.")
      })
  }, [])

  return (
    <main className="home-page">
      <div className="home-content">
        <p className="eyebrow">GOVERNMENT AWARENESS, REIMAGINED</p>

        <h1>Welcome to GovReach AI</h1>

        <p className="description">
          Create evidence-based government awareness campaigns
          in Arabic and English, including text, images, and videos.
        </p>

        <p>
          Backend status: <strong>{backendStatus}</strong>
        </p>

        {error && <p role="alert">{error}</p>}

        <button
          className="primary-button"
          onClick={() => alert("Campaign creation will be implemented next.")}
        >
          Create Your First Campaign
        </button>
      </div>
    </main>
  )
}

export default Home
