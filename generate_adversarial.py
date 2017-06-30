from config import config_dict

import numpy as np
import os

import keras.backend as K
import tensorflow as tf

from src.attackers.deepfool import DeepFool
from src.attackers.fast_gradient import FastGradientMethod
from src.attackers.saliency_map import SaliencyMapMethod
from src.attackers.universal_perturbation import UniversalPerturbation
from src.attackers.virtual_adversarial import VirtualAdversarialMethod
from src.classifiers.utils import load_classifier

from src.utils import get_args, get_verbose_print, load_dataset, make_directory, set_group_permissions_rec

# --------------------------------------------------------------------------------------------------- SETTINGS
args = get_args(__file__)
v_print = get_verbose_print(args.verbose)

# get dataset
(X_train, Y_train), (X_test, Y_test) = load_dataset(args.load)
# X_train, Y_train, X_test, Y_test = X_train[:10], Y_train[:10], X_test[:10], Y_test[:10]

session = tf.Session()
K.set_session(session)

# Load classification model
MODEL_PATH = os.path.join(os.path.abspath(args.load), "")
classifier = load_classifier(MODEL_PATH, "best-weights.h5")

if args.save:
    SAVE_ADV = os.path.join(os.path.abspath(args.save), args.adv_method)
    make_directory(SAVE_ADV)

    with open(os.path.join(SAVE_ADV, "readme.txt"), "w") as wfile:
        wfile.write("Model used for crafting the adversarial examples is in " + MODEL_PATH)

    v_print("Adversarials crafted with", args.adv_method, "on", MODEL_PATH, "will be saved in", SAVE_ADV)

if args.adv_method in ['fgsm', "vat"]:

    if args.adv_method == "fgsm":
        adv_crafter = FastGradientMethod(model=classifier.model, sess=session)
    else:
        adv_crafter = VirtualAdversarialMethod(classifier.model, sess=session)

    for eps in [e / 10 for e in range(1, 11)]:

        X_train_adv = adv_crafter.generate(x_val=X_train, eps=eps, clip_min=0., clip_max=1.)
        X_test_adv = adv_crafter.generate(x_val=X_test, eps=eps, clip_min=0., clip_max=1.)

        if args.save:
            np.save(os.path.join(SAVE_ADV, "eps%.2f_train.npy" % eps), X_train_adv)
            np.save(os.path.join(SAVE_ADV, "eps%.2f_test.npy" % eps), X_test_adv)

else:

    if args.adv_method == 'deepfool':
        adv_crafter = DeepFool(classifier.model, session, clip_min=0., clip_max=1.)
    if args.adv_method == 'jsma':
        adv_crafter = SaliencyMapMethod(classifier.model, sess=session, clip_min=0., clip_max=1., gamma=1., theta=0.1)
    else:
        adv_crafter = UniversalPerturbation(classifier.model, session, p=np.inf,
                                            attacker_params={'clip_min':0., 'clip_max':1.})

    X_train_adv = adv_crafter.generate(x_val=X_train)
    X_test_adv = adv_crafter.generate(x_val=X_test)

    if args.save:
        np.save(os.path.join(SAVE_ADV, "train.npy"), X_train_adv)
        np.save(os.path.join(SAVE_ADV, "test.npy"), X_test_adv)


if args.save:

    # Change files' group and permissions if on ccc
    if config_dict['profile'] == "CLUSTER":
        set_group_permissions_rec(MODEL_PATH)
