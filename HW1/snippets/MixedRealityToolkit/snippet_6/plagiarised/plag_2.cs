using MixedReality.Toolkit.SpatialManipulation;
using MixedReality.Toolkit.UX;
using System.Collections;
using System.Text;
using TMPro;
using UnityEngine;

namespace MixedReality.Toolkit.Examples.Demos
{
    public class BoundsControlRuntimeDemo : MonoBehaviour
    {
        [SerializeField]
        private TextMeshPro statusOutput;

        [SerializeField]
        private Material cubeMat;

        [SerializeField]
        private GameObject boundsVisualsPrefab;

        [SerializeField]
        private Transform demoParent;

        private bool isNextRequested;
        private readonly Vector3 baseCubePosition = new Vector3(0f, 1.2f, 2f);
        private readonly Vector3 baseCubeSize = new Vector3(0.5f, 0.5f, 0.5f);
        private BoundsControl currentBounds;
        private readonly StringBuilder builder = new StringBuilder();

        private void Start()
        {
            StartCoroutine(DemoSequence());
        }

        private void ShowStatus(string message)
        {
            Debug.Assert(statusOutput != null, "statusOutput must be assigned in the inspector.");
            builder.Clear();
            builder.AppendLine(message);
            builder.AppendLine("Use the Next button or say 'next' to proceed.");
            statusOutput.text = builder.ToString();
        }

        private IEnumerator DemoSequence()
        {
            while (true)
            {
                GameObject cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
                cube.GetComponent<MeshRenderer>().material = cubeMat;
                cube.transform.SetParent(demoParent == null ? transform : demoParent);
                cube.transform.position = baseCubePosition;
                cube.transform.localScale = baseCubeSize;

                ShowStatus("Instantiate BoundsControl");
                currentBounds = AttachBoundsControl(cube);
                yield return WaitForUser();

                ShowStatus("Set Target bounds override");
                GameObject overrideRoot = new GameObject("BoundsOverrideRoot");
                overrideRoot.transform.position = new Vector3(0.8f, 0.8f, 1.8f);
                BoxCollider overrideCollider = overrideRoot.AddComponent<BoxCollider>();
                overrideCollider.size = new Vector3(0.162f, 0.1f, 1f);
                currentBounds.OverrideBounds = true;
                currentBounds.BoundsOverride = overrideCollider.transform;
                yield return WaitForUser();

                ShowStatus("Change target bounds override size");
                overrideCollider.size = new Vector3(0.5f, 0.1f, 1f);
                currentBounds.RecomputeBounds();
                yield return WaitForUser();

                ShowStatus("RotateAnchor Object Origin");
                currentBounds.RotateAnchor = RotateAnchorType.ObjectOrigin;
                yield return WaitForUser();

                ShowStatus("RotateAnchor Bounds Center");
                currentBounds.RotateAnchor = RotateAnchorType.BoundsCenter;
                yield return WaitForUser();

                ShowStatus("ScaleAnchor Opposite Corner");
                currentBounds.ScaleAnchor = ScaleAnchorType.OppositeCorner;
                yield return WaitForUser();

                ShowStatus("ScaleAnchor Bounds Center");
                currentBounds.ScaleAnchor = ScaleAnchorType.BoundsCenter;
                yield return WaitForUser();

                ShowStatus("Remove target bounds override");
                currentBounds.OverrideBounds = false;
                currentBounds.BoundsOverride = null;
                Destroy(overrideRoot);
                yield return WaitForUser();

                ShowStatus("FlattenAuto");
                currentBounds.FlattenMode = FlattenMode.Auto;
                yield return WaitForUser();

                ShowStatus("FlattenAlways");
                currentBounds.FlattenMode = FlattenMode.Always;
                yield return WaitForUser();

                ShowStatus("FlattenNever");
                currentBounds.FlattenMode = FlattenMode.Never;
                yield return WaitForUser();

                ShowStatus("BoxPadding 0.2f");
                currentBounds.BoundsPadding = 0.2f;
                yield return WaitForUser();

                ShowStatus("BoxPadding 0");
                currentBounds.BoundsPadding = 0f;
                yield return WaitForUser();

                ShowStatus("Scale X and update rig");
                cube.transform.localScale = new Vector3(1f, 0.5f, 0.5f);
                yield return WaitForUser();

                ShowStatus("Rotate 20 degrees and update rig");
                cube.transform.localRotation = Quaternion.Euler(0f, 20f, 0f);
                yield return WaitForUser();

                ShowStatus("HandleType None");
                currentBounds.EnabledHandles = HandleType.None;
                yield return WaitForUser();

                ShowStatus("HandleType Rotation");
                currentBounds.EnabledHandles = HandleType.Rotation;
                yield return WaitForUser();

                ShowStatus("HandleType Scale");
                currentBounds.EnabledHandles = HandleType.Scale;
                yield return WaitForUser();

                ShowStatus("HandleType Translation");
                currentBounds.EnabledHandles = HandleType.Translation;
                yield return WaitForUser();

                Destroy(cube);

                ShowStatus("Many children");
                GameObject multiRoot = new GameObject("multiRoot");
                Vector3 offset = Vector3.forward * 0.5f;
                multiRoot.transform.position = baseCubePosition + offset;

                Transform parentChain = null;
                const int totalChildren = 10;

                for (int i = 0; i < totalChildren; i++)
                {
                    var childCube = GameObject.CreatePrimitive(PrimitiveType.Cube);
                    childCube.GetComponent<MeshRenderer>().material = cubeMat;
                    childCube.transform.localPosition = Random.insideUnitSphere + baseCubePosition + offset;
                    childCube.transform.rotation = Quaternion.Euler(Random.insideUnitSphere * 360f);
                    childCube.transform.parent = parentChain == null ? multiRoot.transform : parentChain;
                    float baseScale = parentChain == null ? 0.1f : 1f;
                    childCube.transform.localScale = Vector3.one * baseScale;
                    parentChain = childCube.transform;
                }

                currentBounds = AttachBoundsControl(multiRoot);

                ShowStatus("Randomize Child Scale for skewing");
                yield return WaitForUser();

                multiRoot.transform.position += Vector3.forward * 200f;

                var t = multiRoot.transform;
                while (t.childCount > 0)
                {
                    t = t.GetChild(0);
                    float baseScale = parentChain == null ? 0.1f : 1f;
                    t.localScale = new Vector3(
                        baseScale * Random.Range(0.5f, 2f),
                        baseScale * Random.Range(0.5f, 2f),
                        baseScale * Random.Range(0.5f, 2f));
                }

                currentBounds.RecomputeBounds();

                ShowStatus("Delete GameObject");
                yield return WaitForUser();

                Destroy(multiRoot);

                ShowStatus("Done!");
                yield return WaitForUser();
            }
        }

        private BoundsControl AttachBoundsControl(GameObject target)
        {
            target.AddComponent<ConstraintManager>();
            target.AddComponent<ObjectManipulator>();
            var bc = target.AddComponent<BoundsControl>();
            bc.BoundsVisualsPrefab = boundsVisualsPrefab;
            bc.HandlesActive = true;
            bc.DragToggleThreshold = 0.02f;
            target.AddComponent<UGUIInputAdapterDraggable>();
            return bc;
        }

        private IEnumerator WaitForUser()
        {
            while (!isNextRequested)
            {
                yield return null;
            }

            isNextRequested = false;
        }

        public void OnShouldAdvanceSequence()
        {
            isNextRequested = true;
        }
    }
}
