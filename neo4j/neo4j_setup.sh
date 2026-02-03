#!/bin/bash
# neo4j_setup.sh
# Automated setup for Neo4j KG Solution (Linux/Mac)

set -e

echo "============================================================"
echo "Neo4j Knowledge Graph Setup"
echo "============================================================"
echo ""

# Check if Docker is running
if ! docker ps > /dev/null 2>&1; then
    echo "ERROR: Docker is not running!"
    echo "Please start Docker and try again."
    exit 1
fi

echo "[1/5] Starting Neo4j container..."
docker-compose up -d

echo ""
echo "[2/5] Waiting for Neo4j to start (30 seconds)..."
sleep 30

echo ""
echo "[3/5] Installing Python dependencies..."
pip install neo4j || {
    echo "WARNING: Failed to install neo4j package"
    echo "You may need to install it manually: pip install neo4j"
}

echo ""
echo "[4/5] Testing connection..."
python3 load_kg_to_neo4j.py --test || {
    echo "WARNING: Connection test failed"
    echo "Neo4j might still be starting. Wait a minute and try manually."
}

echo ""
echo "[5/5] Setup complete!"
echo ""
echo "============================================================"
echo "Next Steps:"
echo "============================================================"
echo ""
echo "1. Load your KG:"
echo "   python3 load_kg_to_neo4j.py --kg ../MetaQA/kb.txt --clear"
echo ""
echo "2. Query paths:"
echo "   python3 query_neo4j_paths.py --stats"
echo ""
echo "3. Open Neo4j Browser:"
echo "   http://localhost:7474"
echo "   Username: neo4j"
echo "   Password: password123"
echo ""
echo "============================================================"
echo ""
