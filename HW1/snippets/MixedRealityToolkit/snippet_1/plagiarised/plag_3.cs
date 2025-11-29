using System.Collections.Generic;
using UnityEngine;
using TMPro;

namespace MixedReality.Toolkit.Examples.Demos
{
    public class PerfSceneManager : MonoBehaviour
    {
        [SerializeField]
        private GameObject descriptionPanel;

        [SerializeField]
        private GameObject model;

        [SerializeField]
        private TextMeshProUGUI countText;

        [SerializeField]
        private TextMeshProUGUI framerateText;

        [SerializeField]
        private TextMeshProUGUI resultsText;

        [SerializeField]
        private float secondsBetweenFramerateUpdates = 0.25f;

        [SerializeField]
        private GameObject canvasParent;

        [SerializeField]
        private float offset = 0;

        [SerializeField]
        private int columns = 20;

        [SerializeField]
        private int rows = 10;

        [SerializeField]
        private int targetLowFramerate = 50;

        private float secondsSinceLastFramerateUpdate = 0.0f;

        private int currentCount = 0;

        // List for tracking the instantiated objects.
        private List<GameObject> testObjects = new List<GameObject>();

        // Boolean for tracking the end of the test.
        private bool testComplete = true;

        // The current framerate.
        private float frameRate = 0f;

        // Which column is being filled.
        private int yRank = 0;

        // y-Axis local distance for the current instantiated object.
        private float yOffset = 0.0f;

        // Which rank in the z axis is being filled.
        private int zRank = 0;

        // x-Axis local distance for the current instantiated object.
        private float zOffset = 0.0f;

        // How many frames before instantiating the next object.
        private int frameWait = 10;

        // How many frames have had the framerate below the target.
        private int lowFramerateFrameCount = 0;

        /// <summary>
        /// A Unity event function that is called on the frame when a script is enabled just before any of the update methods are called the first time.
        /// </summary> 
        private void Start()
        {
            // prevent divide by zero
            if (columns == 0)
            {
                columns = 20;
            }
        }

        public void StartTest()
        {
            // Trigger the test
            descriptionPanel.SetActive(false);
            resultsText.text = string.Empty;
            lowFramerateFrameCount = 0;
            SetModelCount(0);
            testComplete = false;
        }

        /// <summary>
        /// A Unity event function that is called every frame after normal update functions, if this object is enabled.
        /// </summary>
        private void LateUpdate()
        {
            // Framerate calculations.
            secondsSinceLastFramerateUpdate += Time.deltaTime;
            frameRate = (int)(1.0f / Time.smoothDeltaTime);
            if (secondsSinceLastFramerateUpdate >= secondsBetweenFramerateUpdates)
            {
                framerateText.text = frameRate.ToString();
                secondsSinceLastFramerateUpdate = 0;
            }
        }

        /// <summary>
        /// A Unity event function that is called every frame, if this object is enabled.
        /// </summary>
        private void Update()
        {
            if (testComplete)
            {
                return;
            }

            if (frameRate < targetLowFramerate)
            {
                lowFramerateFrameCount++;
            }

            if (currentCount < 2000 && lowFramerateFrameCount < 60)
            {
                if (frameWait == 0)
                {
                    int cachedCount = currentCount;
                    cachedCount++;
                    SetModelCount(cachedCount);
                    frameWait = 10;
                }
                else
                    frameWait--;
            }
            else
            {
                testComplete = true;
                resultsText.text = $"Test dropped below target framerate after {currentCount} objects.  Test complete.";
                Debug.Log(resultsText.text);
                descriptionPanel.SetActive(true);
            }
        }

        public void SetModelCount(int count)
        {
            if (count < currentCount)
            {
                // delete models
                for(; count < currentCount && testObjects.Count > 0; currentCount--)
                {
                    Destroy(testObjects[testObjects.Count - 1]);
                    testObjects.RemoveAt(testObjects.Count - 1);
                }
            }
            else if (count > currentCount)
            {
                // spawn object
                for(; count > currentCount; currentCount++)
                {
                    var m = Instantiate(model);

                    m.transform.parent = canvasParent.transform;
                    m.transform.localScale = Vector3.one;

                    zRank = currentCount / (rows * columns);
                    zOffset = zRank * offset;
                    yRank = (int)(currentCount / columns);
                    yOffset = (yRank % rows) * offset;
                    m.transform.localPosition = new Vector3((currentCount % columns) * offset, yOffset, zOffset);
                    testObjects.Add(m);
                }
            }

            countText.text = currentCount.ToString();
        }
    }
}