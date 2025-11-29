using MixedReality.Toolkit.SpatialManipulation;
using MixedReality.Toolkit.UX;
using System.Text;
using TMPro;
using UnityEngine;

namespace MixedReality.Toolkit.Examples.Demos
{
    public class BoundsControlStateMachineDemo : MonoBehaviour
    {
        [SerializeField]
        private TextMeshPro statusLabel;

        [SerializeField]
        private Material cubeMaterial;

        [SerializeField]
        private GameObject boundsVisualsPrefab;

        [SerializeField]
        private Transform cubeParent;

        private readonly StringBuilder builder = new StringBuilder();
        private bool advanceRequested;

        private int currentStep;
        private GameObject cube;
        private GameObject multiRoot;
        private GameObject overrideRoot;
        private BoxCollider overrideCollider;
        private Transform lastChildParent;
        private BoundsControl bounds;
        private readonly Vector3 cubePos = new Vector3(0, 1.2f, 2);
        private readonly Vector3 cubeScale = new Vector3(0.5f, 0.5f, 0.5f);

        private void Start()
        {
            currentStep = 0;
            CreateSingleCube();
        }

        private void Update()
        {
            if (!advanceRequested)
            {
                return;
            }

            advanceRequested = false;
            AdvanceStateMachine();
        }

        private void CreateSingleCube()
        {
            cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
            cube.GetComponent<MeshRenderer>().material = cubeMaterial;
            cube.transform.position = cubePos;
            cube.transform.localScale = cubeScale;
            cube.transform.SetParent(cubeParent == null ? transform : cubeParent);
            bounds = SetupBounds(cube);
        }

        private void SetStatus(string text)
        {
            builder.Clear();
            builder.AppendLine(text);
            builder.AppendLine("Press Next or say 'next' to continue.");
            statusLabel.text = builder.ToString();
        }

        private void AdvanceStateMachine()
        {
            switch (currentStep)
            {
                case 0:
                    SetStatus("Instantiate BoundsControl");
                    break;
                case 1:
                    SetStatus("Set Target bounds override");
                    overrideRoot = new GameObject("OverrideBounds");
                    overrideRoot.transform.position = new Vector3(0.8f, 0.8f, 1.8f);
                    overrideCollider = overrideRoot.AddComponent<BoxCollider>();
                    overrideCollider.size = new Vector3(0.162f, 0.1f, 1f);
                    bounds.OverrideBounds = true;
                    bounds.BoundsOverride = overrideCollider.transform;
                    break;
                case 2:
                    SetStatus("Change target bounds override size");
                    overrideCollider.size = new Vector3(0.5f, 0.1f, 1f);
                    bounds.RecomputeBounds();
                    break;
                case 3:
                    SetStatus("RotateAnchor Object Origin");
                    bounds.RotateAnchor = RotateAnchorType.ObjectOrigin;
                    break;
                case 4:
                    SetStatus("RotateAnchor Bounds Center");
                    bounds.RotateAnchor = RotateAnchorType.BoundsCenter;
                    break;
                case 5:
                    SetStatus("ScaleAnchor Opposite Corner");
                    bounds.ScaleAnchor = ScaleAnchorType.OppositeCorner;
                    break;
                case 6:
                    SetStatus("ScaleAnchor Bounds Center");
                    bounds.ScaleAnchor = ScaleAnchorType.BoundsCenter;
                    break;
                case 7:
                    SetStatus("Remove target bounds override");
                    bounds.OverrideBounds = false;
                    bounds.BoundsOverride = null;
                    Destroy(overrideRoot);
                    break;
                case 8:
                    SetStatus("FlattenAuto");
                    bounds.FlattenMode = FlattenMode.Auto;
                    break;
                case 9:
                    SetStatus("FlattenAlways");
                    bounds.FlattenMode = FlattenMode.Always;
                    break;
                case 10:
                    SetStatus("FlattenNever");
                    bounds.FlattenMode = FlattenMode.Never;
                    break;
                case 11:
                    SetStatus("BoxPadding 0.2f");
                    bounds.BoundsPadding = 0.2f;
                    break;
                case 12:
                    SetStatus("BoxPadding 0");
                    bounds.BoundsPadding = 0f;
                    break;
                case 13:
                    SetStatus("Scale X and update rig");
                    cube.transform.localScale = new Vector3(1f, 0.5f, 0.5f);
                    break;
                case 14:
                    SetStatus("Rotate 20 degrees and update rig");
                    cube.transform.localRotation = Quaternion.Euler(0f, 20f, 0f);
                    break;
                case 15:
                    SetStatus("HandleType None");
                    bounds.EnabledHandles = HandleType.None;
                    break;
                case 16:
                    SetStatus("HandleType Rotation");
                    bounds.EnabledHandles = HandleType.Rotation;
                    break;
                case 17:
                    SetStatus("HandleType Scale");
                    bounds.EnabledHandles = HandleType.Scale;
                    break;
                case 18:
                    SetStatus("HandleType Translation");
                    bounds.EnabledHandles = HandleType.Translation;
                    break;
                case 19:
                    Destroy(cube);
                    SetupMultiRoot();
                    SetStatus("Many children");
                    break;
                case 20:
                    SetStatus("Randomize Child Scale for skewing");
                    multiRoot.transform.position += Vector3.forward * 200f;
                    RandomizeChildScales();
                    bounds.RecomputeBounds();
                    break;
                case 21:
                    SetStatus("Delete GameObject");
                    Destroy(multiRoot);
                    break;
                case 22:
                    SetStatus("Done!");
                    break;
                case 23:
                    // restart full demo
                    currentStep = -1;
                    CreateSingleCube();
                    break;
            }

            currentStep++;
        }

        private void SetupMultiRoot()
        {
            multiRoot = new GameObject("multiRoot");
            Vector3 offset = Vector3.forward * 0.5f;
            multiRoot.transform.position = cubePos + offset;

            lastChildParent = null;
            for (int i = 0; i < 10; i++)
            {
                var childCube = GameObject.CreatePrimitive(PrimitiveType.Cube);
                childCube.GetComponent<MeshRenderer>().material = cubeMaterial;
                childCube.transform.localPosition = Random.insideUnitSphere + cubePos + offset;
                childCube.transform.rotation = Quaternion.Euler(Random.insideUnitSphere * 360f);
                childCube.transform.parent = lastChildParent == null ? multiRoot.transform : lastChildParent;
                float baseScale = lastChildParent == null ? 0.1f : 1f;
                childCube.transform.localScale = Vector3.one * baseScale;
                lastChildParent = childCube.transform;
            }

            bounds = SetupBounds(multiRoot);
        }

        private void RandomizeChildScales()
        {
            var t = multiRoot.transform;
            while (t.childCount > 0)
            {
                t = t.GetChild(0);
                float baseScale = lastChildParent == null ? 0.1f : 1f;
                t.localScale = new Vector3(
                    baseScale * Random.Range(0.5f, 2f),
                    baseScale * Random.Range(0.5f, 2f),
                    baseScale * Random.Range(0.5f, 2f));
            }
        }

        private BoundsControl SetupBounds(GameObject target)
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

        public void OnShouldAdvanceSequence()
        {
            advanceRequested = true;
        }
    }
}
