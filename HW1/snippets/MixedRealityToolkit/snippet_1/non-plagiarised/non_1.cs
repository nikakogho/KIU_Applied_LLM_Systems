using System.Collections;
using System.Collections.Generic;
using TMPro;
using UnityEngine;

namespace MixedRealityDemonstrator
{
    /// <summary>
    /// Spawns a growing grid of prefabs until the framerate becomes too low,
    /// then reports how many instances were active at that point.
    /// </summary>
    public class FrameStressTester : MonoBehaviour
    {
        [Header("UI")]
        [SerializeField] private GameObject infoPanel;
        [SerializeField] private TextMeshProUGUI countLabel;
        [SerializeField] private TextMeshProUGUI fpsLabel;
        [SerializeField] private TextMeshProUGUI resultLabel;

        [Header("Prefab & Layout")]
        [SerializeField] private GameObject prefab;
        [SerializeField] private Transform parentTransform;
        [SerializeField] private float spacing = 0.25f;
        [SerializeField] private int columns = 20;
        [SerializeField] private int rows = 10;

        [Header("Test Settings")]
        [SerializeField] private int maxInstances = 2000;
        [SerializeField] private int targetFps = 50;
        [SerializeField] private float spawnIntervalSeconds = 0.15f;
        [SerializeField] private float fpsLabelUpdateSeconds = 0.25f;
        [SerializeField] private int lowFpsFrameTolerance = 60;

        private readonly List<GameObject> _instances = new List<GameObject>();
        private Coroutine _testRoutine;
        private bool _testRunning;

        private float _smoothedFps;
        private float _fpsUiTimer;
        private int _consecutiveLowFpsFrames;

        private void Awake()
        {
            if (columns <= 0)
            {
                columns = 20;
            }

            if (rows <= 0)
            {
                rows = 10;
            }
        }

        /// <summary>
        /// Called from UI to start a new performance test.
        /// </summary>
        public void BeginTest()
        {
            // Clean up any previous run.
            if (_testRoutine != null)
            {
                StopCoroutine(_testRoutine);
                _testRoutine = null;
            }

            ClearInstances();

            _testRunning = true;
            _consecutiveLowFpsFrames = 0;
            _smoothedFps = 0f;
            _fpsUiTimer = 0f;

            resultLabel.text = string.Empty;
            infoPanel.SetActive(false);

            _testRoutine = StartCoroutine(TestRoutine());
        }

        private void Update()
        {
            if (!_testRunning)
            {
                return;
            }

            // Compute a simple smoothed FPS value.
            float instantFps = 1f / Mathf.Max(Time.unscaledDeltaTime, 0.0001f);
            _smoothedFps = Mathf.Lerp(_smoothedFps <= 0 ? instantFps : _smoothedFps, instantFps, 0.15f);

            // Track how long FPS has been below target.
            if (_smoothedFps < targetFps)
            {
                _consecutiveLowFpsFrames++;
            }
            else
            {
                _consecutiveLowFpsFrames = 0;
            }

            // Periodically update FPS UI.
            _fpsUiTimer += Time.unscaledDeltaTime;
            if (_fpsUiTimer >= fpsLabelUpdateSeconds)
            {
                fpsLabel.text = Mathf.RoundToInt(_smoothedFps).ToString();
                _fpsUiTimer = 0f;
            }
        }

        private IEnumerator TestRoutine()
        {
            while (_instances.Count < maxInstances &&
                   _consecutiveLowFpsFrames < lowFpsFrameTolerance)
            {
                SpawnNextInstance();
                yield return new WaitForSeconds(spawnIntervalSeconds);
            }

            FinishTest();
        }

        private void SpawnNextInstance()
        {
            var go = Instantiate(prefab, parentTransform);
            go.transform.localScale = Vector3.one;
            go.transform.localPosition = ComputePosition(_instances.Count);

            _instances.Add(go);
            countLabel.text = _instances.Count.ToString();
        }

        /// <summary>
        /// Compute a 3D grid position for the object at the given index.
        /// Layout is layers along Z, each layer is a rows x columns grid.
        /// </summary>
        private Vector3 ComputePosition(int index)
        {
            int layerSize = rows * columns;
            int layer = index / layerSize;
            int indexInLayer = index % layerSize;

            int row = indexInLayer / columns;
            int col = indexInLayer % columns;

            float x = col * spacing;
            float y = row * spacing;
            float z = layer * spacing;

            return new Vector3(x, y, z);
        }

        private void FinishTest()
        {
            _testRunning = false;
            _testRoutine = null;

            string msg =
                $"Framerate dropped below {targetFps} FPS with {_instances.Count} instances active. Test finished.";
            resultLabel.text = msg;
            Debug.Log(msg);

            infoPanel.SetActive(true);
        }

        private void ClearInstances()
        {
            for (int i = _instances.Count - 1; i >= 0; i--)
            {
                if (_instances[i] != null)
                {
                    Destroy(_instances[i]);
                }
            }

            _instances.Clear();
            countLabel.text = "0";
        }
    }
}
